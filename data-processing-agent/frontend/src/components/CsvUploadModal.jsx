import React, { useState } from 'react';
import { Modal, Box, SpaceBetween, Button, FileUpload, Alert } from '@cloudscape-design/components';

const CsvUploadModal = ({ visible, onDismiss, onUpload, loading }) => {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [error, setError] = useState(null);

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select a CSV file');
      return;
    }

    const file = selectedFiles[0];
    const reader = new FileReader();

    reader.onload = async (e) => {
      try {
        const content = e.target.result;
        await onUpload({ name: file.name, content });
        setSelectedFiles([]);
        setError(null);
        onDismiss();
      } catch (err) {
        setError(err.message);
      }
    };

    reader.readAsText(file);
  };

  return (
    <Modal
      visible={visible}
      onDismiss={onDismiss}
      header="Upload CSV File"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss}>Cancel</Button>
            <Button variant="primary" onClick={handleUpload} loading={loading}>
              Upload
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="l">
        {error && <Alert type="error">{error}</Alert>}
        <FileUpload
          onChange={({ detail }) => setSelectedFiles(detail.value)}
          value={selectedFiles}
          i18nStrings={{
            uploadButtonText: e => e ? "Choose files" : "Choose file",
            dropzoneText: e => e ? "Drop files to upload" : "Drop file to upload",
            removeFileAriaLabel: e => `Remove file ${e + 1}`,
            limitShowFewer: "Show fewer files",
            limitShowMore: "Show more files",
            errorIconAriaLabel: "Error"
          }}
          showFileLastModified
          showFileSize
          showFileThumbnail
          tokenLimit={3}
          constraintText="CSV files only"
        />
      </SpaceBetween>
    </Modal>
  );
};

export default CsvUploadModal;
