# db_services.py
import os
import re
import time
from zipfile import ZipFile
from django.db.models import Count, Sum
from .models import PDFDocument, WordCluster, CatalogSimilarity
from .services import decode_zip_filename, extract_text_from_pdf, generate_wordcloud_from_texts
from .cluster_services import perform_kmeans_clustering, perform_dbscan_clustering, find_optimal_clusters


def extract_year_quarter_from_path(catalog_path):
    year = None
    quarter = None
    if catalog_path and catalog_path != '/':
        for part in catalog_path.split('/'):
            if re.fullmatch(r'\d{4}', part):
                year = int(part)
            elif re.fullmatch(r'(0[1-4])', part):
                quarter = int(part)
    return year, quarter


def save_pdf_document(zip_archive_name, relative_path, text_content=None, wordcloud_data=None):
    relative_path = relative_path.replace('\\', '/')
    file_name = os.path.basename(relative_path)

    if '/' in relative_path:
        catalog_path = '/'.join(relative_path.split('/')[:-1])
        catalog_parts = catalog_path.split('/')
        catalog_name = catalog_parts[-1] if catalog_parts else 'root'
    else:
        catalog_path = '/'
        catalog_name = 'root'

    defaults = {
        'file_name': file_name,
        'catalog_path': catalog_path,
        'catalog_name': catalog_name,
    }
    if text_content is not None:
        defaults['text_length'] = len(text_content)

    if wordcloud_data and 'words' in wordcloud_data:
        top_words = [
            {'word': w['text'], 'count': w.get('weight', 0), 'size': w.get('size', 14)}
            for w in wordcloud_data['words'][:50]
        ]
        defaults['top_words'] = top_words
        defaults['wordcloud_data'] = wordcloud_data

    doc, created = PDFDocument.objects.update_or_create(
        zip_archive_name=zip_archive_name,
        relative_path=relative_path,
        defaults=defaults
    )
    return doc, created


def save_pdf_documents(zip_path, zip_filename, force_reload=False):
    print(f"Сохранение PDF документов из {zip_filename}")
    stats = {'total_pdf': 0, 'successfully_processed': 0, 'failed': 0, 'existing': 0}

    with ZipFile(zip_path, 'r') as zip_ref:
        all_files = zip_ref.namelist()
        pdf_files = []
        for encoded_name in all_files:
            if encoded_name.endswith('/'):
                continue
            if encoded_name.lower().endswith('.pdf'):
                decoded_name = decode_zip_filename(encoded_name)
                pdf_files.append({'encoded': encoded_name, 'decoded': decoded_name})

        stats['total_pdf'] = len(pdf_files)
        print(f"Найдено PDF файлов: {stats['total_pdf']}")

        for idx, file_info in enumerate(pdf_files, 1):
            print(f"Обработка [{idx}/{stats['total_pdf']}]: {file_info['decoded']}")
            try:
                existing = PDFDocument.objects.filter(
                    zip_archive_name=zip_filename,
                    relative_path=file_info['decoded']
                ).first()
                if existing and existing.extracted_text and not force_reload:
                    print(f"Уже существует: {file_info['decoded']}")
                    stats['existing'] += 1
                    continue

                if '/' in file_info['decoded']:
                    catalog_path = '/'.join(file_info['decoded'].split('/')[:-1])
                    file_name = file_info['decoded'].split('/')[-1]
                    catalog_parts = catalog_path.split('/')
                    catalog_name = catalog_parts[-1] if catalog_parts else 'root'
                else:
                    catalog_path = '/'
                    file_name = file_info['decoded']
                    catalog_name = 'root'

                year, quarter = extract_year_quarter_from_path(catalog_path)

                with zip_ref.open(file_info['encoded']) as f:
                    pdf_bytes = f.read()
                    extracted_text = extract_text_from_pdf(pdf_bytes)
                if not extracted_text:
                    extracted_text = ""

                wordcloud_data = None
                top_words = None
                if extracted_text and len(extracted_text.strip()) > 0:
                    wordcloud_data = generate_wordcloud_from_texts([extracted_text])
                    if wordcloud_data and 'words' in wordcloud_data:
                        top_words = [
                            {'word': w['text'], 'count': w.get('weight', 0), 'size': w.get('size', 14)}
                            for w in wordcloud_data['words'][:50]
                        ]

                doc, created = PDFDocument.objects.update_or_create(
                    zip_archive_name=zip_filename,
                    relative_path=file_info['decoded'],
                    defaults={
                        'file_name': file_name,
                        'catalog_path': catalog_path,
                        'catalog_name': catalog_name,
                        'year': year,
                        'quarter': quarter,
                        'extracted_text': extracted_text,
                        'text_length': len(extracted_text),
                        'top_words': top_words,
                        'wordcloud_data': wordcloud_data
                    }
                )
                stats['successfully_processed'] += 1
            except Exception as e:
                print(f"Ошибка при сохранении {file_info['decoded']}: {e}")
                stats['failed'] += 1
    return stats


def get_all_catalog_paths(zip_filename):
    paths = PDFDocument.objects.filter(zip_archive_name=zip_filename).values_list('relative_path', flat=True)
    catalogs = set()
    for path in paths:
        parts = path.split('/')
        for i in range(1, len(parts)):
            catalogs.add('/'.join(parts[:i]))
    return sorted(catalogs)


def prepare_clustering_data(zip_filename, catalog_path):
    if catalog_path == '/':
        docs = PDFDocument.objects.filter(zip_archive_name=zip_filename)
    else:
        docs = PDFDocument.objects.filter(zip_archive_name=zip_filename, relative_path__startswith=catalog_path + '/')
    if not docs.exists():
        return None

    word_doc_matrix = {}
    word_freq = {}
    for doc in docs:
        if doc.top_words:
            for w in doc.top_words:
                word = w['word']
                count = w['count']
                if word not in word_doc_matrix:
                    word_doc_matrix[word] = set()
                word_doc_matrix[word].add(doc.id)
                word_freq[word] = word_freq.get(word, 0) + count

    if len(word_freq) < 3:
        return None

    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:30]
    words = [w for w, _ in top_words]
    frequencies = [f for _, f in top_words]

    n = len(words)
    matrix = [[0] * n for _ in range(n)]
    for i, w1 in enumerate(words):
        docs1 = word_doc_matrix.get(w1, set())
        for j, w2 in enumerate(words):
            if i <= j:
                docs2 = word_doc_matrix.get(w2, set())
                common = len(docs1.intersection(docs2))
                matrix[i][j] = common
                matrix[j][i] = common
    return {'words': words, 'frequencies': frequencies, 'matrix': matrix}


def cluster_single_catalog(zip_filename, catalog_path, method='kmeans', **kwargs):
    try:
        data = prepare_clustering_data(zip_filename, catalog_path)
        if not data or len(data['words']) < 3:
            return {'status': 'skipped', 'reason': 'too_few_words'}

        if method == 'kmeans':
            n_clusters = kwargs.get('n_clusters')
            if not n_clusters:
                n_clusters = find_optimal_clusters(data['words'], data['matrix'], data['frequencies'])
            if n_clusters < 2:
                return {'status': 'skipped', 'reason': 'optimal_clusters_lt_2'}
            result = perform_kmeans_clustering(data['words'], data['matrix'], data['frequencies'], n_clusters)
            parameters = {'n_clusters': n_clusters, 'auto': kwargs.get('auto_clusters', True)}
        elif method == 'dbscan':
            eps = kwargs.get('eps', 0.5)
            min_samples = kwargs.get('min_samples', 2)
            result = perform_dbscan_clustering(data['words'], data['matrix'], data['frequencies'], eps, min_samples)
            parameters = {'eps': eps, 'min_samples': min_samples}
        else:
            return {'status': 'failed', 'reason': f'unknown method {method}'}

        if not result:
            return {'status': 'failed', 'reason': 'clustering returned None'}

        WordCluster.objects.update_or_create(
            zip_archive_name=zip_filename,
            catalog_path=catalog_path,
            algorithm=method,
            defaults={'parameters': parameters, 'clusters_data': result}
        )
        return {'status': 'success', 'n_clusters': result['statistics']['n_clusters'], 'total_words': len(data['words'])}
    except Exception as e:
        print(f"Ошибка кластеризации {catalog_path}: {e}")
        return {'status': 'error', 'error': str(e)}


def cluster_all_catalogs(zip_filename, catalog_paths):
    print(f"Начинаем кластеризацию {len(catalog_paths)} каталогов")
    stats = {'total': len(catalog_paths), 'success': 0, 'skipped': 0, 'failed': 0, 'errors': 0}
    for i, catalog_path in enumerate(catalog_paths, 1):
        print(f"  [{i}/{len(catalog_paths)}] {catalog_path}")
        result = cluster_single_catalog(zip_filename, catalog_path)
        if result['status'] == 'success':
            stats['success'] += 1
            print(f"{result['n_clusters']} кластеров")
        elif result['status'] == 'skipped':
            stats['skipped'] += 1
            print(f"Пропущен: {result.get('reason', 'unknown')}")
        elif result['status'] == 'failed':
            stats['failed'] += 1
            print(f"Ошибка: {result.get('reason', 'unknown')}")
        else:
            stats['errors'] += 1
            print(f"Исключение: {result.get('error', 'unknown')}")
    print(f"Кластеризация завершена: {stats}")
    return stats


def calculate_catalog_similarity(zip_filename, path1, path2):
    cluster1 = WordCluster.objects.filter(zip_archive_name=zip_filename, catalog_path=path1, algorithm='kmeans').first()
    cluster2 = WordCluster.objects.filter(zip_archive_name=zip_filename, catalog_path=path2, algorithm='kmeans').first()
    if not cluster1 or not cluster2:
        return 0.0

    words1 = set()
    words2 = set()
    if cluster1.clusters_data and 'clusters' in cluster1.clusters_data:
        for c in cluster1.clusters_data['clusters']:
            if 'top_words' in c:
                words1.update(w['word'] for w in c['top_words'] if 'word' in w)
    if cluster2.clusters_data and 'clusters' in cluster2.clusters_data:
        for c in cluster2.clusters_data['clusters']:
            if 'top_words' in c:
                words2.update(w['word'] for w in c['top_words'] if 'word' in w)

    if not words1 or not words2:
        return 0.0
    inter = len(words1 & words2)
    union = len(words1 | words2)
    return inter / union if union > 0 else 0.0


def find_all_similar_catalogs(zip_filename):
    print(f"Поиск похожих каталогов в {zip_filename}")
    paths = WordCluster.objects.filter(zip_archive_name=zip_filename, algorithm='kmeans').values_list('catalog_path', flat=True)
    path_list = list(paths)
    print(f"Сравниваем {len(path_list)} каталогов")

    stats = {'total_pairs': 0, 'similar_found': 0}
    CatalogSimilarity.objects.filter(zip_archive_name=zip_filename).delete()

    for i, path1 in enumerate(path_list):
        for path2 in path_list[i+1:]:
            stats['total_pairs'] += 1
            sim = calculate_catalog_similarity(zip_filename, path1, path2)
            if sim > 0.1:
                CatalogSimilarity.objects.create(
                    zip_archive_name=zip_filename,
                    source_catalog=path1,
                    target_catalog=path2,
                    similarity_score=sim,
                )
                CatalogSimilarity.objects.create(
                    zip_archive_name=zip_filename,
                    source_catalog=path2,
                    target_catalog=path1,
                    similarity_score=sim,
                )
                stats['similar_found'] += 1
                if stats['similar_found'] % 100 == 0:
                    print(f"  ...найдено {stats['similar_found']} пар")
    print(f"Поиск похожих завершен: найдено {stats['similar_found']} пар")
    return stats


def initialize_archive_in_db(zip_path, zip_filename, force_reload=False):
    start_time = time.time()

    if force_reload:
        print("\n🗑Удаление старых данных...")
        pdf_deleted = PDFDocument.objects.filter(zip_archive_name=zip_filename).delete()
        cluster_deleted = WordCluster.objects.filter(zip_archive_name=zip_filename).delete()
        sim_deleted = CatalogSimilarity.objects.filter(zip_archive_name=zip_filename).delete()
        print(f"   PDF: {pdf_deleted[0]}, Кластеры: {cluster_deleted[0]}, Похожесть: {sim_deleted[0]}")

    print("\nШАГ 1: Сохранение PDF документов...")
    pdf_stats = save_pdf_documents(zip_path, zip_filename, force_reload)
    print(f" PDF обработано: {pdf_stats}")

    print("\nШАГ 2: Получение списка каталогов...")
    all_catalogs = get_all_catalog_paths(zip_filename)
    print(f"Найдено каталогов: {len(all_catalogs)}")

    print("\nШАГ 3: Кластеризация каталогов...")
    clustering_stats = cluster_all_catalogs(zip_filename, all_catalogs)
    print(f"Кластеризация завершена")

    print("\nШАГ 4: Поиск похожих каталогов...")
    similarity_stats = find_all_similar_catalogs(zip_filename)
    print(f"Поиск похожих завершен")

    elapsed = time.time() - start_time
    print(f"\nИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА за {elapsed:.1f} сек")
    return {
        'pdf': pdf_stats,
        'clustering': clustering_stats,
        'similarity': similarity_stats,
        'elapsed_seconds': round(elapsed, 1)
    }


def get_catalog_data_from_db(zip_filename, catalog_path):
    if catalog_path != '/':
        catalog_path = catalog_path.rstrip('/')
    documents = PDFDocument.objects.filter(
        zip_archive_name=zip_filename,
        relative_path__startswith=catalog_path if catalog_path != '/' else ''
    ).order_by('relative_path')
    if not documents.exists():
        return None

    all_texts = [doc.extracted_text for doc in documents if doc.extracted_text]
    subcatalogs = set()
    for doc in documents:
        if catalog_path == '/':
            rest_path = doc.relative_path
        else:
            rest_path = doc.relative_path.replace(catalog_path + '/', '', 1)
        if '/' in rest_path:
            subcatalogs.add(rest_path.split('/')[0])

    catalog_wordcloud = generate_wordcloud_from_texts(all_texts) if all_texts else None
    path_parts = catalog_path.split('/') if catalog_path != '/' else []
    catalog_name = path_parts[-1] if path_parts else 'root'

    all_top_words = []
    word_document_matrix = {}
    for doc in documents:
        if doc.top_words:
            all_top_words.extend(doc.top_words)
            for w in doc.top_words:
                word = w['word']
                if word not in word_document_matrix:
                    word_document_matrix[word] = set()
                word_document_matrix[word].add(doc.id)

    if all_top_words:
        word_freq = {}
        for w in all_top_words:
            word = w['word']
            count = w['count']
            word_freq[word] = word_freq.get(word, 0) + count
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
        max_count = sorted_words[0][1]
        combined_top_words = [
            {'word': w, 'count': c, 'size': 14 + (c / max_count) * 46}
            for w, c in sorted_words
        ]
        top_words_for_clustering = [w for w, _ in sorted_words[:30]]
        n = len(top_words_for_clustering)
        cooc = [[0]*n for _ in range(n)]
        for i, w1 in enumerate(top_words_for_clustering):
            for j, w2 in enumerate(top_words_for_clustering):
                if i <= j:
                    common = len(word_document_matrix.get(w1, set()) & word_document_matrix.get(w2, set()))
                    cooc[i][j] = common
                    cooc[j][i] = common
    else:
        combined_top_words = []
        cooc = []
        top_words_for_clustering = []
        word_freq = {}

    return {
        'catalogName': catalog_name,
        'fullPath': catalog_path,
        'pathParts': path_parts,
        'filesCount': documents.count(),
        'pdfFilesProcessed': len(all_texts),
        'wordcloud': catalog_wordcloud,
        'subcatalogs': sorted(list(subcatalogs)),
        'documents': [
            {
                'id': doc.id,
                'file_name': doc.file_name,
                'relative_path': doc.relative_path.replace(catalog_path + '/', '') if catalog_path != '/' else doc.relative_path,
                'text_length': doc.text_length,
                'top_words': doc.top_words[:10] if doc.top_words else []
            } for doc in documents
        ],
        'all_top_words': combined_top_words[:50],
        'is_end_catalog': len(subcatalogs) == 0,
        'clustering_data': {
            'words': top_words_for_clustering,
            'cooccurrence_matrix': cooc,
            'word_frequencies': [word_freq.get(w, 0) for w in top_words_for_clustering]
        }
    }


def find_similar_catalogs_from_db(zip_filename, target_path):
    if target_path == '/':
        target_name = 'root'
    else:
        target_name = target_path.rstrip('/').split('/')[-1]
    print(f"Поиск каталогов с именем '{target_name}' (кроме {target_path})")

    all_docs = PDFDocument.objects.filter(zip_archive_name=zip_filename).values_list('relative_path', flat=True)
    catalog_paths = set()
    for path in all_docs:
        parts = path.split('/')
        for i in range(1, len(parts)):
            catalog_paths.add('/'.join(parts[:i]))
    print(f"Найдено уникальных каталогов: {len(catalog_paths)}")

    similar = []
    for cp in catalog_paths:
        if cp == target_path:
            continue
        if cp == '/':
            name = 'root'
        else:
            name = cp.split('/')[-1]
        if name == target_name:
            files_count = PDFDocument.objects.filter(
                zip_archive_name=zip_filename,
                relative_path__startswith=cp + '/' if cp != '/' else ''
            ).count()
            preview = PDFDocument.objects.filter(
                zip_archive_name=zip_filename,
                relative_path__startswith=cp + '/' if cp != '/' else ''
            ).values_list('file_name', flat=True)[:5]
            similar.append({
                'name': name,
                'path': cp,
                'filesCount': files_count,
                'preview_files': list(preview)
            })
    print(f"Найдено похожих каталогов: {len(similar)}")
    return similar


def check_archive_exists(zip_filename):
    return PDFDocument.objects.filter(zip_archive_name=zip_filename).exists()


def get_archive_stats(zip_filename):
    return {
        'total_documents': PDFDocument.objects.filter(zip_archive_name=zip_filename).count(),
        'total_clusters': WordCluster.objects.filter(zip_archive_name=zip_filename).count(),
        'total_similarities': CatalogSimilarity.objects.filter(zip_archive_name=zip_filename).count()
    }