# Enum for document types
from enum import Enum


class DocumentType(str, Enum):
    LAB_REPORTS = "lab_reports"
    PRESCRIPTION = "prescription"
    IMAGING = "imaging"
    MEDICAL_RECORD = "medical_record"
    OTHER = "other"
