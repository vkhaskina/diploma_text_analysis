from django.db import models
import json


class PDFDocument(models.Model):
    """Модель для хранения информации о PDF файлах"""
    zip_archive_name = models.CharField(max_length=255)
    relative_path = models.CharField(max_length=512)
    file_name = models.CharField(max_length=255)

    extracted_text = models.TextField(null=True, blank=True)
    text_length = models.IntegerField(null=True, blank=True)

    top_words = models.JSONField(null=True, blank=True)
    wordcloud_data = models.JSONField(null=True, blank=True)

    catalog_path = models.CharField(max_length=512)
    catalog_name = models.CharField(max_length=255)

    year = models.IntegerField(null=True, blank=True)
    quarter = models.IntegerField(null=True, blank=True)
    class Meta:
        unique_together = ['zip_archive_name', 'relative_path']
        indexes = [
            models.Index(fields=['zip_archive_name']),
            models.Index(fields=['catalog_path']),
            models.Index(fields=['catalog_name']),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.zip_archive_name})"

    def get_top_words_list(self):
        """Возвращает топ слова"""
        if self.top_words:
            return json.loads(self.top_words)
        return []

    def get_wordcloud_data_dict(self):
        """Возвращает данные облака слов"""
        if self.wordcloud_data:
            return json.loads(self.wordcloud_data)
        return {}

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class WordCluster(models.Model):
    zip_archive_name = models.CharField(max_length=255)
    catalog_path = models.CharField(max_length=512)
    algorithm = models.CharField(max_length=50)
    parameters = models.JSONField(default=dict)
    clusters_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('zip_archive_name', 'catalog_path', 'algorithm')

class CatalogSimilarity(models.Model):
    """Похожесть между каталогами"""
    zip_archive_name = models.CharField(max_length=255)
    source_catalog = models.CharField(max_length=512)
    target_catalog = models.CharField(max_length=512)

    similarity_score = models.FloatField()  # от 0 до 1

    class Meta:
        unique_together = ['zip_archive_name', 'source_catalog', 'target_catalog']
        indexes = [
            models.Index(fields=['zip_archive_name', 'source_catalog']),
        ]

    def __str__(self):
        return f"{self.source_catalog} → {self.target_catalog}: {self.similarity_score}"
