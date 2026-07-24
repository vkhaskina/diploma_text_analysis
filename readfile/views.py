import os
import tempfile
import re

from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .db_services import (
    check_archive_exists,
    get_archive_stats,
    initialize_archive_in_db,
    get_catalog_data_from_db
)
from .services import start_process, find_all_end_catalogs
from .cluster_services import (
    perform_kmeans_clustering,
    find_optimal_clusters
)
from .models import PDFDocument

@api_view(['POST'])
@csrf_exempt
def read_input(request):
    zip_file = request.FILES.get('zip_file')
    force_reload = request.data.get('force_reload', False)

    if not zip_file:
        return Response({"status": "error", "message": "Файл не был загружен"}, status=400)

    if not zip_file.name.endswith('.zip'):
        return Response({"status": "error", "message": "Пожалуйста, загрузите ZIP архив"}, status=400)

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            for chunk in zip_file.chunks():
                tmp_file.write(chunk)
            temp_path = tmp_file.name

        try:
            structure = start_process(temp_path)
            end_catalogs = find_all_end_catalogs(structure)

            catalog_buttons = [
                {
                    "id": i + 1,
                    "path": catalog,
                    "name": catalog.split('/')[-1] if catalog != '/' else 'root',
                    "label": catalog[:27] + "..." if len(catalog) > 30 else catalog
                }
                for i, catalog in enumerate(end_catalogs)
            ]

            archive_exists = check_archive_exists(zip_file.name)

            if archive_exists and not force_reload:
                print(f"Архив {zip_file.name} уже существует")
                db_stats = get_archive_stats(zip_file.name)

                request.session['zip_filename'] = zip_file.name
                request.session['db_initialized'] = True
                request.session.save()

                return Response({
                    "status": "success",
                    "message": "Архив уже обработан",
                    "file_name": zip_file.name,
                    "file_size": zip_file.size,
                    "catalog_buttons": catalog_buttons,
                    "end_catalogs_count": len(end_catalogs),
                    "db_initialized": True,
                    "db_stats": db_stats,
                    "from_cache": True
                })
            else:
                if force_reload:
                    print(f"Принудительная перезагрузка {zip_file.name}")

                init_stats = initialize_archive_in_db(temp_path, zip_file.name, force_reload)

                request.session['zip_filename'] = zip_file.name
                request.session['db_initialized'] = True
                request.session.save()

                return Response({
                    "status": "success",
                    "message": "Архив загружен и полностью обработан",
                    "file_name": zip_file.name,
                    "file_size": zip_file.size,
                    "catalog_buttons": catalog_buttons,
                    "end_catalogs_count": len(end_catalogs),
                    "db_initialized": True,
                    "init_stats": init_stats,
                    "from_cache": False
                })

        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
def cleanup_session(request):
    """Очистка сессии"""
    try:
        temp_path = request.session.get('temp_zip_path')
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        request.session.flush()
        return Response({"status": "success", "message": "Сессия очищена"})
    except Exception as e:
        return Response({
            "status": "error",
            "message": f"Ошибка при очистке: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def analyze_catalog(request):
    try:
        document_id = request.data.get('document_id')
        catalog_path = request.data.get('catalog_path')
        method = request.data.get('method', 'kmeans')
        n_clusters = request.data.get('n_clusters', None)
        auto_clusters = request.data.get('auto_clusters', True)
        eps = request.data.get('eps', 0.5)
        min_samples = request.data.get('min_samples', 2)
        force = request.data.get('force', False)

        zip_filename = request.session.get('zip_filename')
        if not zip_filename:
            return Response({"status": "error", "message": "Сессия устарела"}, status=400)

        if document_id:
            from .models import PDFDocument
            try:
                doc = PDFDocument.objects.get(id=document_id, zip_archive_name=zip_filename)
            except PDFDocument.DoesNotExist:
                return Response({"status": "error", "message": "Документ не найден"}, status=404)

            result = {
                'status': 'success',
                'type': 'document',
                'id': doc.id,
                'file_name': doc.file_name,
                'catalog_path': doc.catalog_path,
                'text_length': doc.text_length,
                'wordcloud': doc.wordcloud_data,
                'top_words': doc.top_words[:50] if doc.top_words else [],
            }
            return Response(result)

        if not catalog_path:
            return Response({"status": "error", "message": "Не указан путь"}, status=400)


        catalog_data = get_catalog_data_from_db(zip_filename, catalog_path)
        if not catalog_data:
            return Response({"status": "error", "message": "Нет данных"}, status=404)

        from .models import WordCluster
        from .db_services import prepare_clustering_data

        cluster_data = None
        if method == 'kmeans':
            cluster_data = prepare_clustering_data(zip_filename, catalog_path)

        existing = WordCluster.objects.filter(
            zip_archive_name=zip_filename,
            catalog_path=catalog_path,
            algorithm=method
        ).first()

        if existing and not force:
            catalog_data['clustering'] = existing.clusters_data
            print(f"Использованы существующие кластеры для {catalog_path} (метод {method})")
        else:
            if cluster_data is None:
                cluster_data = prepare_clustering_data(zip_filename, catalog_path)

            from .cluster_services import find_optimal_clusters
            from .cluster_services import perform_kmeans_clustering

            if cluster_data and len(cluster_data['words']) >= 3:
                if method == 'kmeans':
                    if auto_clusters:
                        n_clusters = find_optimal_clusters(
                            cluster_data['words'],
                            cluster_data['matrix'],
                            cluster_data['frequencies'],
                        )
                    elif not n_clusters:
                        n_clusters = min(5, len(cluster_data['words']))
                    if n_clusters >= 2:
                        result = perform_kmeans_clustering(
                            cluster_data['words'],
                            cluster_data['matrix'],
                            cluster_data['frequencies'],
                            n_clusters
                        )
                        parameters = {'n_clusters': n_clusters, 'auto': auto_clusters}
                elif method == 'dbscan':
                    from .cluster_services import perform_dbscan_clustering
                    result = perform_dbscan_clustering(
                        cluster_data['words'],
                        cluster_data['matrix'],
                        cluster_data['frequencies'],
                        eps=eps,
                        min_samples=min_samples
                    )
                    parameters = {'eps': eps, 'min_samples': min_samples}
                else:
                    return Response({"error": "Unsupported method"}, status=400)

                if result:
                    WordCluster.objects.update_or_create(
                        zip_archive_name=zip_filename,
                        catalog_path=catalog_path,
                        algorithm=method,
                        defaults={
                            'parameters': parameters,
                            'clusters_data': result
                        }
                    )
                    catalog_data['clustering'] = result
                    print(f"Созданы новые кластеры для {catalog_path} (метод {method})")

        from .models import CatalogSimilarity
        from .db_services import find_similar_catalogs_from_db

        similar = CatalogSimilarity.objects.filter(
            zip_archive_name=zip_filename,
            source_catalog=catalog_path,
        ).order_by('-similarity_score')[:10]

        catalog_data['similar_catalogs'] = [
            {'path': s.target_catalog, 'similarity': s.similarity_score}
            for s in similar
        ]

        catalog_data['similar_by_name'] = find_similar_catalogs_from_db(zip_filename, catalog_path)

        catalog_data['status'] = 'success'
        return Response(catalog_data)

    except Exception as e:
        print(f"Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({"status": "error", "message": str(e)}, status=500)

@api_view(['POST'])
def cluster_trend(request):
    try:
        catalog_path = request.data.get('catalog_path')
        cluster_id = request.data.get('cluster_id')
        method = request.data.get('method', 'kmeans')
        zip_filename = request.session.get('zip_filename')

        if not catalog_path or cluster_id is None or not zip_filename:
            return Response({"error": "Не указаны catalog_path, cluster_id"}, status=400)

        from .models import WordCluster, PDFDocument
        word_cluster = WordCluster.objects.filter(
            zip_archive_name=zip_filename,
            catalog_path=catalog_path,
            algorithm=method
        ).first()

        if not word_cluster:
            return Response({"error": f"Кластеры для метода {method} не найдены"}, status=404)

        clusters_data = word_cluster.clusters_data
        if not clusters_data or 'clusters' not in clusters_data:
            return Response({"error": "Нет данных о кластерах"}, status=404)

        target_cluster = None
        for cl in clusters_data['clusters']:
            if cl['id'] == cluster_id:
                target_cluster = cl
                break

        if not target_cluster:
            return Response({"error": "Кластер не найден"}, status=404)

        cluster_words = set()
        for w in target_cluster.get('top_words', []):
            cluster_words.add(w['word'])
        for w in target_cluster.get('words', [])[:10]:
            cluster_words.add(w)

        docs = PDFDocument.objects.filter(zip_archive_name=zip_filename)

        from collections import defaultdict
        trend_data = defaultdict(lambda: {'count': 0, 'total_docs': 0})

        for doc in docs:
            if doc.year is None or doc.quarter is None:
                continue
            key = (doc.year, doc.quarter)
            trend_data[key]['total_docs'] += 1
            doc_words = set()
            if doc.top_words:
                for w in doc.top_words:
                    doc_words.add(w['word'])
            if doc_words.intersection(cluster_words):
                trend_data[key]['count'] += 1

        result = []
        for (year, quarter), data in sorted(trend_data.items()):
            result.append({
                'year': year,
                'quarter': quarter,
                'count': data['count'],
                'total_docs': data['total_docs'],
                'ratio': data['count'] / data['total_docs'] if data['total_docs'] > 0 else 0
            })

        print(f"Динамика кластера (глобально): каталог={catalog_path}, метод={method}, кластер={cluster_id}")
        print(f"Ключевые слова: {cluster_words}")
        print(f"Всего документов в архиве: {docs.count()}")
        print(f"С year/quarter: {docs.exclude(year=None).exclude(quarter=None).count()}")

        return Response(result)

    except Exception as e:
        print(f"Ошибка в cluster_trend: {e}")
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
def keyword_search(request):
    query = request.data.get('query', '').strip()
    limit = request.data.get('limit', 10)

    if not query:
        return Response({"error": "Пустой запрос"}, status=400)

    words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]{2,}\b', query.lower())
    if not words:
        return Response({"results": []})

    zip_filename = request.session.get('zip_filename')
    docs = PDFDocument.objects.filter(zip_archive_name=zip_filename) if zip_filename else PDFDocument.objects.all()

    results = []
    for doc in docs:
        if not doc.extracted_text:
            continue
        text = doc.extracted_text.lower()
        match_count = sum(1 for w in words if w in text)
        if match_count:
            results.append({
                'id': doc.id,
                'file_name': doc.file_name,
                'catalog_path': doc.catalog_path,
                'match_count': match_count,
                'text_length': doc.text_length,
            })

    results.sort(key=lambda x: x['match_count'], reverse=True)
    return Response(results[:limit])

