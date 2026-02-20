# Design Document

## Overview

This design outlines the implementation of a simplified dashboard interface that replaces multiple sections with a single unified "Artifacts" section. The solution consolidates file upload functionality and removes unnecessary metric widgets to create a cleaner, more focused user experience.

## Architecture

### Current State
- Multiple dashboard sections: Active Use Cases (1), Completed (1), In Progress (5), Industries
- Separate material sections: First Call Deck Materials, Demo Materials, Reference Architecture
- Scattered file upload functionality across different forms

### Target State
- Single "Artifacts" section with unified file upload functionality
- Consolidated file management for PPT, PDF, Video, and Architecture images
- Clean dashboard layout without metric widgets

## Components and Interfaces

### Frontend Components

#### ArtifactsSection Component
```javascript
// New unified artifacts management component
const ArtifactsSection = {
  props: ['onCancel'],
  state: {
    uploadedFiles: [],
    isUploading: false,
    selectedFiles: []
  },
  methods: {
    handleFileUpload,
    handleFileDelete,
    validateFileType,
    displayFiles
  }
}
```

#### Updated Dashboard Layout
- Remove metric widget components (ActiveUseCases, Completed, InProgress, Industries)
- Remove separate material section components
- Add single ArtifactsSection component
- Update navigation to reflect new structure

### Backend Components

#### File Storage Service
- S3 bucket for artifact storage
- File metadata storage (DynamoDB or RDS)
- File type validation
- Upload progress tracking

#### API Endpoints
```
POST /api/artifacts/upload - Upload new artifacts
GET /api/artifacts - List all artifacts
DELETE /api/artifacts/{id} - Delete specific artifact
GET /api/artifacts/{id} - Download specific artifact
```

## Data Models

### Artifact Model
```javascript
{
  id: string,
  filename: string,
  fileType: 'ppt' | 'pdf' | 'video' | 'image',
  category: 'presentation' | 'demo' | 'architecture' | 'general',
  uploadDate: timestamp,
  fileSize: number,
  s3Key: string,
  uploadedBy: string,
  metadata: {
    originalName: string,
    mimeType: string,
    description?: string
  }
}
```

### Updated Dashboard State
```javascript
{
  // Remove these states:
  // showActiveUseCases, showCompleted, showInProgress, showIndustries
  // showFirstCallDeck, showDemoMaterials, showReferenceArchitecture
  
  // Add:
  showArtifacts: boolean,
  artifacts: Artifact[]
}
```

## Error Handling

### File Upload Validation
- File type validation (PPT, PDF, Video, Images)
- File size limits
- Virus scanning
- Duplicate file handling

### Error States
- Upload failures with retry mechanism
- Network connectivity issues
- Storage quota exceeded
- Invalid file format errors

## Testing Strategy

### Unit Tests
- ArtifactsSection component functionality
- File upload validation logic
- File type detection
- Error handling scenarios

### Integration Tests
- End-to-end file upload workflow
- Dashboard layout after section removal
- Navigation functionality
- File management operations (upload, view, delete)

### User Acceptance Tests
- Verify single Artifacts section displays correctly
- Confirm all old sections are removed
- Test file upload for all supported types
- Validate responsive design across devices
- Ensure no broken links or references remain