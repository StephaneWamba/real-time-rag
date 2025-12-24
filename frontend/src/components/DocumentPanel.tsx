import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import type { Document } from '../services/api';

const ITEMS_PER_PAGE = 4;

export default function DocumentPanel() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEditor, setShowEditor] = useState(false);
  const [editingDoc, setEditingDoc] = useState<Document | null>(null);
  const [formData, setFormData] = useState({ title: '', content: '' });
  const [currentPage, setCurrentPage] = useState(1);
  const [totalDocs, setTotalDocs] = useState(0);

  useEffect(() => {
    loadDocuments();
    const interval = setInterval(loadDocuments, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await apiService.getDocuments();
      setTotalDocs(response.length);
      setDocuments(response);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setDocuments([]);
      setTotalDocs(0);
    } finally {
      setLoading(false);
    }
  };

  const paginatedDocuments = documents.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );
  const totalPages = Math.ceil(documents.length / ITEMS_PER_PAGE);

  const handleSave = async () => {
    try {
      if (editingDoc) {
        await apiService.updateDocument(editingDoc.id, formData);
      } else {
        await apiService.createDocument(formData);
      }
      setShowEditor(false);
      setEditingDoc(null);
      setFormData({ title: '', content: '' });
      loadDocuments();
    } catch (error) {
      console.error('Failed to save document:', error);
    }
  };

  const handleEdit = (doc: Document) => {
    setEditingDoc(doc);
    setFormData({ title: doc.title, content: doc.content });
    setShowEditor(true);
  };

  return (
    <div className="panel bottom-panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Knowledge Base</h2>
          <p className="panel-description">
            <strong>Add or edit documents here.</strong> When you save a document, watch it automatically flow through the pipeline above. Changes are processed in real-time—no manual reindexing needed.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => {
          setEditingDoc(null);
          setFormData({ title: '', content: '' });
          setShowEditor(true);
        }}>
          + Add
        </button>
      </div>

      {showEditor && (
        <div style={{ marginBottom: '1rem', padding: '1rem', border: '1px solid var(--border)', borderRadius: '6px' }}>
          <input
            className="input"
            placeholder="Document title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            style={{ marginBottom: '0.5rem' }}
          />
          <textarea
            className="input textarea"
            placeholder="Document content"
            value={formData.content}
            onChange={(e) => setFormData({ ...formData, content: e.target.value })}
          />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button className="btn btn-primary" onClick={handleSave}>Save</button>
            <button className="btn" onClick={() => {
              setShowEditor(false);
              setEditingDoc(null);
            }}>Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--text-secondary)' }}>Loading documents...</p>
      ) : (
        <>
          <div className="list">
            {paginatedDocuments.map((doc) => (
              <div key={doc.id} className="list-item">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                  <div>
                    <strong>{doc.title}</strong>
                    <span className="badge" style={{ marginLeft: '0.5rem' }}>v{doc.version}</span>
                  </div>
                  <button className="btn" onClick={() => handleEdit(doc)} style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}>
                    Edit
                  </button>
                </div>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                  {doc.content.substring(0, 100)}...
                </p>
              </div>
            ))}
          </div>
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}-{Math.min(currentPage * ITEMS_PER_PAGE, documents.length)} of {documents.length}
              </span>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  className="btn"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  style={{ opacity: currentPage === 1 ? 0.5 : 1 }}
                >
                  Previous
                </button>
                <button
                  className="btn"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  style={{ opacity: currentPage === totalPages ? 0.5 : 1 }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

