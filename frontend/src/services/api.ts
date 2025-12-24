import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8003';
const UPDATE_API_URL = import.meta.env.VITE_UPDATE_API_URL || 'http://localhost:8002';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

const updateApi = axios.create({
  baseURL: UPDATE_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Document {
  id: string;
  title: string;
  content: string;
  version: number;
  created_at?: string;
  updated_at?: string;
}

export interface QueryRequest {
  query: string;
  top_k?: number;
  page?: number;
  page_size?: number;
}

export interface QueryResponse {
  answer: string;
  sources: Array<{
    document_id: string;
    score: number;
    version: number;
    cited: boolean;
  }>;
  confidence: number;
  is_complete: boolean;
  pagination?: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface HealthStatus {
  status: string;
  dependencies: {
    [key: string]: {
      status: string;
      latency_ms?: number;
      error?: string;
    };
  };
}

export const apiService = {
  // Query endpoints
  async query(request: QueryRequest): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>('/query', request);
    return response.data;
  },

  async getHealth(): Promise<HealthStatus> {
    const response = await api.get<HealthStatus>('/health');
    return response.data;
  },

  async getCollections(): Promise<{ collections: string[] }> {
    const response = await api.get<{ collections: string[] }>('/collections');
    return response.data;
  },

  // Document endpoints
  async getDocuments(): Promise<Document[]> {
    const response = await updateApi.get<{ documents: Document[] }>('/api/documents');
    return response.data.documents;
  },

  async createDocument(doc: Omit<Document, 'id' | 'version' | 'created_at' | 'updated_at'>): Promise<Document> {
    const response = await updateApi.post<Document>('/api/documents', doc);
    return response.data;
  },

  async updateDocument(id: string, doc: Partial<Document>): Promise<Document> {
    const response = await updateApi.put<Document>(`/api/documents/${id}`, doc);
    return response.data;
  },

  async deleteDocument(id: string): Promise<void> {
    await updateApi.delete(`/api/documents/${id}`);
  },

  // Metrics endpoints
  async getPipelineStatus(): Promise<{
    stages: Record<string, number>;
    total_latency: number;
    last_update: string | null;
    recent_updates_count: number;
  }> {
    const response = await updateApi.get('/api/pipeline/status');
    return response.data;
  },

  async getUpdateMetrics(): Promise<{
    updates: {
      total: number;
      lag_samples: number[];
    };
    last_update: string | null;
  }> {
    const response = await updateApi.get('/api/metrics');
    return response.data;
  },

  async getQueryMetrics(): Promise<{
    queries: {
      total: number;
      latency_samples: number[];
    };
  }> {
    const response = await api.get('/api/metrics');
    return response.data;
  },
};

