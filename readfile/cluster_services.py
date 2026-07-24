import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import colorsys
from collections import Counter
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

def convert_to_serializable(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    else:
        return obj

def generate_cluster_colors(n_clusters):
    colors = []
    for i in range(n_clusters):
        hue = i / n_clusters
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
        hex_color = '#{:02x}{:02x}{:02x}'.format(
            int(rgb[0] * 255),
            int(rgb[1] * 255),
            int(rgb[2] * 255)
        )
        colors.append(hex_color)
    return colors

def perform_kmeans_clustering(words, cooccurrence_matrix, word_frequencies, n_clusters=5):
    if len(words) < n_clusters:
        return None

    X = np.array(cooccurrence_matrix, dtype=float)
    frequencies = np.array(word_frequencies, dtype=float).reshape(-1, 1)
    max_freq = np.max(frequencies) if np.max(frequencies) > 0 else 1
    frequencies = frequencies / max_freq
    X = np.hstack([X, frequencies])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    distances = kmeans.transform(X_scaled).min(axis=1)
    silhouette = None
    unique_labels = set(labels)
    if len(unique_labels) >= 2:
        try:
            silhouette = silhouette_score(X_scaled, labels, metric='euclidean')
        except:
            silhouette = None

    clusters = {}
    for i, (word, label) in enumerate(zip(words, labels)):
        label = int(label)
        if label not in clusters:
            clusters[label] = []
        clusters[label].append({
            'word': word,
            'frequency': int(word_frequencies[i]),
            'distance': float(distances[i])
        })

    for label in clusters:
        clusters[label].sort(key=lambda x: x['frequency'], reverse=True)

    colors = generate_cluster_colors(n_clusters)

    result_clusters = []
    for label in range(n_clusters):
        if label in clusters:
            cluster_words = clusters[label]
            result_clusters.append({
                'id': label,
                'size': len(cluster_words),
                'words': [w['word'] for w in cluster_words[:15]],
                'top_words': [
                    {'word': w['word'], 'frequency': w['frequency']}
                    for w in cluster_words[:5]
                ],
                'color': colors[label],
                'cohesion': float(np.mean([w['distance'] for w in cluster_words]))
            })

    pca = PCA(n_components=2)
    coords = pca.fit_transform(X_scaled)
    projection_data = [
        {"word": words[i], "cluster": int(labels[i]), "x": float(coords[i][0]), "y": float(coords[i][1])}
        for i in range(len(words))
    ]

    result_dict = {
        'clusters': result_clusters,
        'statistics': {
            'total_words': len(words),
            'n_clusters': n_clusters,
            'inertia': float(kmeans.inertia_),
            'method': 'kmeans',
            'silhouette_score': silhouette
        },
        'projection': projection_data
    }
    return convert_to_serializable(result_dict)


def perform_dbscan_clustering(words, cooccurrence_matrix, word_frequencies, eps=0.5, min_samples=2):
    if len(words) < 3:
        return None

    X = np.array(cooccurrence_matrix, dtype=float)
    frequencies = np.array(word_frequencies, dtype=float).reshape(-1, 1)
    max_freq = np.max(frequencies) if np.max(frequencies) > 0 else 1
    frequencies = frequencies / max_freq
    X = np.hstack([X, frequencies])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    db = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
    labels = db.fit_predict(X_scaled)

    silhouette = None
    non_noise_mask = labels != -1
    if np.sum(non_noise_mask) >= 2 and len(set(labels[non_noise_mask])) >= 2:
        X_filtered = X_scaled[non_noise_mask]
        labels_filtered = labels[non_noise_mask]
        try:
            silhouette = silhouette_score(X_filtered, labels_filtered, metric='euclidean')
        except:
            silhouette = None

    noise_ratio = np.sum(labels == -1) / len(labels)
    unique_labels = set(labels)
    n_clusters = len(unique_labels - {-1})

    if n_clusters == 0:
        return None

    clusters = {}
    for i, (word, label) in enumerate(zip(words, labels)):
        if label == -1:
            continue
        if label not in clusters:
            clusters[label] = []
        clusters[label].append({
            'word': word,
            'frequency': int(word_frequencies[i]),
            'distance': 0.0
        })

    for label in clusters:
        clusters[label].sort(key=lambda x: x['frequency'], reverse=True)

    label_mapping = {old: i for i, old in enumerate(sorted(clusters.keys()))}
    mapped_clusters = {}
    for old, items in clusters.items():
        new = label_mapping[old]
        mapped_clusters[new] = items

    colors = generate_cluster_colors(n_clusters)

    result_clusters = []
    for label in range(n_clusters):
        if label in mapped_clusters:
            cluster_words = mapped_clusters[label]
            result_clusters.append({
                'id': label,
                'size': len(cluster_words),
                'words': [w['word'] for w in cluster_words[:15]],
                'top_words': [
                    {'word': w['word'], 'frequency': w['frequency']}
                    for w in cluster_words[:5]
                ],
                'color': colors[label],
                'cohesion': 0.0
            })

    pca = PCA(n_components=2)
    coords = pca.fit_transform(X_scaled)
    projection_data = [
        {"word": words[i], "cluster": int(labels[i]), "x": float(coords[i][0]), "y": float(coords[i][1])}
        for i in range(len(words))
    ]

    result_dict = {
        'clusters': result_clusters,
        'statistics': {
            'total_words': len(words),
            'n_clusters': n_clusters,
            'method': 'dbscan',
            'eps': eps,
            'min_samples': min_samples,
            'silhouette_score': silhouette,
            'noise_ratio': noise_ratio
        },
        'projection': projection_data
    }
    return result_dict

def find_optimal_clusters(words, cooccurrence_matrix, word_frequencies, max_clusters=10):
    if len(words) < 3:
        return 2

    max_possible = min(max_clusters, len(words) // 2)
    if max_possible < 2:
        return 2

    X = np.array(cooccurrence_matrix, dtype=float)
    frequencies = np.array(word_frequencies, dtype=float).reshape(-1, 1)
    max_freq = np.max(frequencies) if np.max(frequencies) > 0 else 1
    frequencies = frequencies / max_freq
    X = np.hstack([X, frequencies])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    inertias = []
    K = range(2, max_possible + 1)

    for k in K:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        inertias.append(kmeans.inertia_)

    if len(inertias) >= 2:
        diffs = np.diff(inertias)
        second_diffs = np.diff(diffs)
        if len(second_diffs) > 0:
            optimal = int(np.argmin(second_diffs) + 2)
            return min(optimal, max_possible)

    return min(5, max_possible)

def compute_elbow_data(words, cooccurrence_matrix, word_frequencies, max_k=10):
    if len(words) < 3:
        return {'ks': [], 'inertias': []}

    max_possible = min(max_k, len(words) - 1)
    if max_possible < 2:
        return {'ks': [], 'inertias': []}

    X = np.array(cooccurrence_matrix, dtype=float)
    frequencies = np.array(word_frequencies, dtype=float).reshape(-1, 1)
    max_freq = np.max(frequencies) if np.max(frequencies) > 0 else 1
    frequencies = frequencies / max_freq
    X = np.hstack([X, frequencies])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    ks = []
    inertias = []
    for k in range(2, max_possible + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        ks.append(k)
        inertias.append(kmeans.inertia_)

    return {'ks': ks, 'inertias': inertias}