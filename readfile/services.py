from io import BytesIO
from zipfile import ZipFile
import re
from collections import Counter
import PyPDF2
import spacy
from pdfminer.high_level import extract_text_to_fp, extract_text
from pdfminer.layout import LAParams
import pymorphy3

morph = pymorphy3.MorphAnalyzer()

custom_stopwords = {
    'рис', 'рисунок', 'рисунке', 'рисунком', 'рисунков', 'рисунками',
    'табл', 'таблица', 'таблице', 'таблицей', 'таблиц', 'таблицами',
    'см', 'смотри', 'примечание', 'примечания',
    'дан', 'данные', 'данных', 'данным', 'данными',
    'получен', 'полученные', 'полученных', 'полученным',
    'проведен', 'проведенные', 'проведенных', 'проведенным',
    'рассмотрен', 'рассмотренные', 'рассмотренных', 'рассмотренным',
    'указан', 'указанные', 'указанных', 'указанным',
    'представлен', 'представленные', 'представленных', 'представленным',
    'использован', 'использованные', 'использованных', 'использованным',
    'разработан', 'разработанные', 'разработанных', 'разработанным',
    'создан', 'созданные', 'созданных', 'созданным',
    'найден', 'найденные', 'найденных', 'найденным',
    'показан', 'показанные', 'показанных', 'показанным',
    'описан', 'описанные', 'описанных', 'описанным',
}

nlp_ru = spacy.load("ru_core_news_sm")
nlp_en = spacy.load("en_core_web_sm")

russian_stopwords = nlp_ru.Defaults.stop_words
english_stopwords = nlp_en.Defaults.stop_words

base_stopwords = russian_stopwords.union(english_stopwords)

all_stopwords = base_stopwords.union(custom_stopwords)

def decode_zip_filename(filename):
    encodings = ['cp866', 'windows-1251', 'cp1251', 'koi8-r', 'utf-8']
    for enc in encodings:
        try:
            return filename.encode('cp437').decode(enc)
        except:
            continue
    return filename

def build_zip_structure(zip_file):
    # Используем обычный dict вместо defaultdict
    structure = {}

    for item in zip_file.infolist():
        decoded_name = decode_zip_filename(item.filename)

        if item.is_dir():
            parts = decoded_name.rstrip('/').split('/')
            if len(parts) > 1:
                parent_dir = '/'.join(parts[:-1])
                # Проверяем существование ключа
                if parent_dir not in structure:
                    structure[parent_dir] = []
                structure[parent_dir].append({
                    'name': parts[-1],
                    'type': 'dir',
                    'full_path': decoded_name
                })
            else:
                if '/' not in structure:
                    structure['/'] = []
                structure['/'].append({
                    'name': parts[0],
                    'type': 'dir',
                    'full_path': decoded_name
                })
        else:
            parts = decoded_name.split('/')
            if len(parts) > 1:
                dir_path = '/'.join(parts[:-1])
                if dir_path not in structure:
                    structure[dir_path] = []
                structure[dir_path].append({
                    'name': parts[-1],
                    'type': 'file',
                    'full_path': decoded_name
                })
            else:
                if '/' not in structure:
                    structure['/'] = []
                structure['/'].append({
                    'name': parts[0],
                    'type': 'file',
                    'full_path': decoded_name
                })

    return structure

def find_all_end_catalogs(structure):
    all_directories = set()

    for dir_path in structure.keys():
        if dir_path:
            all_directories.add(dir_path.rstrip('/'))

    for dir_path, items in structure.items():
        for item in items:
            if item['type'] == 'dir':
                full_path = item['full_path'].rstrip('/')
                if full_path:
                    all_directories.add(full_path)

    if '/' in structure:
        all_directories.add('/')

    end_catalogs = []

    for catalog_path in all_directories:
        normalized_path = catalog_path if catalog_path != '/' else '/'

        has_subdirs = False

        if normalized_path in structure:
            for item in structure[normalized_path]:
                if item['type'] == 'dir':
                    has_subdirs = True
                    break

        if not has_subdirs:
            end_catalogs.append(normalized_path)

    return sorted(end_catalogs)

def extract_text_from_pdf(pdf_bytes):
    try:
        pdf_file = BytesIO(pdf_bytes)

        laparams = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5,
            detect_vertical=True,
            all_texts=True
        )

        text = extract_text(pdf_file, laparams=laparams)

        if not text:
            return ""

        def fix_encoding_issues(text):
            replacements = {
                '¸': 'ё',
                '¨': 'ё',
                '`': 'ё',
                'È': 'Е',
                '�': '',
            }
            for wrong, correct in replacements.items():
                text = text.replace(wrong, correct)
            return text

        def join_hyphenated_words(text):
            text = fix_encoding_issues(text)

            pattern1 = r'(\w+)-\s*[\n\r]\s*(\w+)'
            text = re.sub(pattern1, r'\1\2', text)

            pattern2 = r'(\w+)-\s+(\w+)'
            text = re.sub(pattern2, r'\1\2', text)

            text = text.replace('\xad', '')

            return text

        processed_text = join_hyphenated_words(text)

        return processed_text

    except Exception as e:
        print(f"Ошибка pdfminer при чтении PDF: {e}")


def generate_wordcloud_from_texts(texts, max_words=50, min_word_length=3):
    if not texts:
        return None

    all_text = ' '.join(texts)
    words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]{' + str(min_word_length) + r',}\b', all_text.lower())
    filtered_words = [w for w in words if w not in all_stopwords]

    if not filtered_words:
        return None

    # Лемматизация
    lemmatized = []
    for w in filtered_words:
        try:
            lemma = morph.parse(w)[0].normal_form
            lemmatized.append(lemma)
        except:
            lemmatized.append(w)

    word_counts = Counter(lemmatized)
    top_words = word_counts.most_common(max_words)

    if not top_words:
        return None

    max_count = top_words[0][1]
    words_data = [
        {
            "text": word,
            "weight": count,
            "size": 14 + (count / max_count) * 46
        }
        for word, count in top_words
    ]

    return {
        "words": words_data,
        "totalWords": len(lemmatized),
        "uniqueWords": len(word_counts),
        "topWords": [word for word, _ in top_words[:5]]
    }

def start_process(zip_name):
    with ZipFile(zip_name, 'r') as myzip:
        structure = build_zip_structure(myzip)
    return structure

