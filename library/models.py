from django.db import models

class Book(models.model):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    isbn = models.CharField(max_length=13, unique=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.title
