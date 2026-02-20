import React, { useState, useRef } from 'react';
import { 
  Container, 
  Header, 
  Button, 
  SpaceBetween,
  Box,
  FileUpload,
  Table,
  Badge,
  Modal,
  Alert
} from '@cloudscape-design/components';

const ArtifactsSection = ({ onCancel }) => {
  const [files, setFiles] = useState([]);
  const [uploadedArtifacts, setUploadedArtifacts] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedArtifact, setSelectedArtifact] = useState(null);
  const [uploadError, setUploadError] = useState('');

  const fileInputRef = useRef(null);

  // Supported file types
  const supportedTypes = {
    'application/vnd.ms-powerpoint': 'PPT',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PPTX',
    'application/pdf': 'PDF',
    'video/mp4': 'MP4',
    'video/avi': 'AVI',
    'video/mov': 'MOV',
    'image/jpeg': 'JPEG',
    'image/jpg': 'JPG',
    'image/png': 'PNG',
    'image/gif': 'GIF',
    'image/svg+xml': 'SVG'
  };

  const validateFile = (file) => {
    // Check file type
    if (!supportedTypes[file.type]) {
      return `Unsupported file type: ${file.type}. Supported types: PPT, PPTX, PDF, Video (MP4, AVI, MOV), Images (JPEG, PNG, GIF, SVG)`;
    }

    // Check file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      return `File size too large: ${(file.size / 1024 / 1024).toFixed(2)}MB. Maximum size: 50MB`;
    }

    return null;
  };

  const handleFileChange = ({ detail }) => {
    setFiles(detail.value);
    setUploadError('');
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setUploadError('Please select files to upload');
      return;
    }

    setIsUploading(true);
    setUploadError('');

    try {
      const newArtifacts = [];

      for (const file of files) {
        const validationError = validateFile(file);
        if (validationError) {
          setUploadError(validationError);
          setIsUploading(false);
          return;
        }

        // Simulate file upload (in real implementation, this would upload to S3)
        const artifact = {
          id: Date.now() + Math.random(),
          filename: file.name,
          fileType: supportedTypes[file.type],
          fileSize: file.size,
          uploadDate: new Date().toISOString(),
          category: getCategoryFromType(supportedTypes[file.type]),
          file: file // In real implementation, this would be the S3 URL
        };

        newArtifacts.push(artifact);
      }

      // Add to uploaded artifacts
      setUploadedArtifacts(prev => [...prev, ...newArtifacts]);
      setFiles([]);
      
    } catch (error) {
      setUploadError('Upload failed: ' + error.message);
    } finally {
      setIsUploading(false);
    }
  };

  const getCategoryFromType = (fileType) => {
    if (['PPT', 'PPTX'].includes(fileType)) return 'Presentation';
    if (fileType === 'PDF') return 'Document';
    if (['MP4', 'AVI', 'MOV'].includes(fileType)) return 'Video';
    if (['JPEG', 'JPG', 'PNG', 'GIF', 'SVG'].includes(fileType)) return 'Image';
    return 'Other';
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleDelete = (artifact) => {
    setSelectedArtifact(artifact);
    setShowDeleteModal(true);
  };

  const confirmDelete = () => {
    setUploadedArtifacts(prev => prev.filter(item => item.id !== selectedArtifact.id));
    setShowDeleteModal(false);
    setSelectedArtifact(null);
  };

  const handleDownload = (artifact) => {
    // In real implementation, this would download from S3
    const url = URL.createObjectURL(artifact.file);
    const a = document.createElement('a');
    a.href = url;
    a.download = artifact.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const columns = [
    {
      id: 'filename',
      header: 'File Name',
      cell: item => <strong>{item.filename}</strong>,
      sortingField: 'filename',
      isRowHeader: true
    },
    {
      id: 'category',
      header: 'Category',
      cell: item => <Badge color="blue">{item.category}</Badge>,
      sortingField: 'category'
    },
    {
      id: 'fileType',
      header: 'Type',
      cell: item => <Badge>{item.fileType}</Badge>,
      sortingField: 'fileType'
    },
    {
      id: 'fileSize',
      header: 'Size',
      cell: item => formatFileSize(item.fileSize),
      sortingField: 'fileSize'
    },
    {
      id: 'uploadDate',
      header: 'Upload Date',
      cell: item => new Date(item.uploadDate).toLocaleDateString(),
      sortingField: 'uploadDate'
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: item => (
        <SpaceBetween direction="horizontal" size="xs">
          <Button
            iconName="download"
            variant="icon"
            onClick={() => handleDownload(item)}
            ariaLabel={`Download ${item.filename}`}
          />
          <Button
            iconName="remove"
            variant="icon"
            onClick={() => handleDelete(item)}
            ariaLabel={`Delete ${item.filename}`}
          />
        </SpaceBetween>
      )
    }
  ];

  return (
    <>
      <Container 
        header={
          <Header 
            variant="h2" 
            counter={`(${uploadedArtifacts.length})`}
            actions={
              <Button onClick={onCancel}>
                Back
              </Button>
            }
          >
            Artifacts
          </Header>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          {uploadError && (
            <Alert type="error" dismissible onDismiss={() => setUploadError('')}>
              {uploadError}
            </Alert>
          )}

          <Box>
            <SpaceBetween direction="vertical" size="m">
              <Header variant="h3">Upload New Artifacts</Header>
              <FileUpload
                onChange={handleFileChange}
                value={files}
                i18nStrings={{
                  uploadButtonText: e => e ? "Choose files" : "Choose file",
                  dropzoneText: e => e ? "Drop files to upload" : "Drop file to upload",
                  removeFileAriaLabel: e => `Remove file ${e + 1}`,
                  limitShowFewer: "Show fewer files",
                  limitShowMore: "Show more files",
                  errorIconAriaLabel: "Error"
                }}
                multiple
                accept=".ppt,.pptx,.pdf,.mp4,.avi,.mov,.jpeg,.jpg,.png,.gif,.svg"
                showFileLastModified
                showFileSize
                showFileThumbnail
                constraintText="Supported formats: PPT, PPTX, PDF, Video (MP4, AVI, MOV), Images (JPEG, PNG, GIF, SVG). Maximum file size: 50MB."
              />
              
              <Box float="right">
                <Button 
                  variant="primary" 
                  onClick={handleUpload}
                  loading={isUploading}
                  disabled={files.length === 0 || isUploading}
                >
                  Upload Artifacts
                </Button>
              </Box>
            </SpaceBetween>
          </Box>

          {uploadedArtifacts.length > 0 && (
            <Box>
              <Header variant="h3">Uploaded Artifacts</Header>
              <Table
                items={uploadedArtifacts}
                columnDefinitions={columns}
                sortingDisabled={false}
                empty={
                  <Box margin={{ vertical: 'xs' }} textAlign="center">
                    <SpaceBetween size="m">
                      <b>No artifacts</b>
                      <p>No artifacts have been uploaded yet.</p>
                    </SpaceBetween>
                  </Box>
                }
              />
            </Box>
          )}
        </SpaceBetween>
      </Container>

      <Modal
        visible={showDeleteModal}
        onDismiss={() => setShowDeleteModal(false)}
        header="Delete Artifact"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button onClick={() => setShowDeleteModal(false)}>Cancel</Button>
              <Button variant="primary" onClick={confirmDelete}>Delete</Button>
            </SpaceBetween>
          </Box>
        }
      >
        <p>Are you sure you want to delete "{selectedArtifact?.filename}"? This action cannot be undone.</p>
      </Modal>
    </>
  );
};

export default ArtifactsSection;