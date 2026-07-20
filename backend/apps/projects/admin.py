from django.contrib import admin
from .models import Project, ProjectAssignment, ProjectComment, ProjectDeliverable, ProjectDocument
admin.site.register([Project, ProjectAssignment, ProjectDeliverable, ProjectComment, ProjectDocument])
