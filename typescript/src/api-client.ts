/**
 * API Client for Java Unit Test Agent
 * Provides methods to interact with the FastAPI backend
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

export interface IndexRequest {
    project_path: string;
    force?: boolean;
    project_id?: string;
}

export interface IndexResponse {
    status: string;
    indexed_files: number;
    parsed_classes: number;
    methods_count: number;
    steps: string[];
    errors: string[];
    project_id: string;
    duration: number;
}

export interface StatsResponse {
    methods_in_graph: number;
    vectors_stored: number;
    collection_status: string;
    indexed_files?: number;
}

export interface HealthResponse {
    status: string;
    timestamp: string;
    version: string;
    components: {
        graph: boolean;
        embedder: boolean;
        vector_store: boolean;
        indexer_agent: boolean;
    };
}

export interface TestGenerationRequest {
    target_method: string;
    class_name?: string;
    file_path?: string;
    project_id?: string;
}

export interface TestGenerationResponse {
    status: string;
    test_code: string;
    quality_score: number;
    suggestions: string[];
    method_name: string;
    duration: number;
}

export class JavaTestAgentClient {
    private client: AxiosInstance;
    private baseURL: string;

    constructor(baseURL: string = 'http://localhost:8000') {
        this.baseURL = baseURL;
        this.client = axios.create({
            baseURL,
            timeout: 300000, // 5 minutes for long operations
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }

    /**
     * Check API health
     */
    async health(): Promise<HealthResponse> {
        try {
            const response = await this.client.get<HealthResponse>('/health');
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    /**
     * Index a Java project
     */
    async indexProject(request: IndexRequest): Promise<IndexResponse> {
        try {
            console.log(`📂 Indexing project: ${request.project_path}`);
            const response = await this.client.post<IndexResponse>(
                '/api/index/project',
                request
            );
            console.log(`✅ Indexed ${response.data.indexed_files} files`);
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    /**
     * Get project statistics
     */
    async getStats(): Promise<StatsResponse> {
        try {
            const response = await this.client.get<StatsResponse>('/api/stats');
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    /**
     * Generate unit test for a method using RAG system
     * Uses Markov walks + vector search for context gathering
     */
    async generateTest(request: TestGenerationRequest): Promise<TestGenerationResponse> {
        try {
            console.log(`🧪 Generating test for: ${request.target_method}`);
            const response = await this.client.post<TestGenerationResponse>(
                '/api/generate/test',
                request
            );
            console.log(`✅ Test generated (quality: ${response.data.quality_score.toFixed(1)}/100)`);
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    /**
     * Handle API errors
     */
    private handleError(error: unknown): Error {
        if (axios.isAxiosError(error)) {
            const axiosError = error as AxiosError;
            if (axiosError.response) {
                const detail = (axiosError.response.data as any)?.detail || axiosError.message;
                return new Error(`API Error: ${detail}`);
            } else if (axiosError.request) {
                return new Error('No response from API. Is the server running?');
            }
        }
        return error as Error;
    }

    /**
     * Get base URL
     */
    getBaseURL(): string {
        return this.baseURL;
    }
}

// Export singleton instance
export const apiClient = new JavaTestAgentClient();

