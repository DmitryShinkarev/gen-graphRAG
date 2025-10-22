/**
 * Java Unit Test Agent - Continue.dev Integration
 * Main entry point for Continue.dev extension
 */

export { JavaTestAgentClient, apiClient } from './api-client';
export { indexProjectCommand } from './slash-commands/index-project';
export { statsCommand } from './slash-commands/stats';
export { testRagCommand } from './slash-commands/test-rag';

export * from './api-client';

// For Continue.dev configuration
export const continueConfig = {
    name: 'Java Unit Test Agent',
    version: '0.1.0',
    description: 'AI-powered Java unit test generation with RAG',
    
    slashCommands: [
        {
            name: 'index',
            description: 'Index Java project for test generation',
            params: {
                path: {
                    description: 'Project path (optional, defaults to workspace)',
                    required: false
                }
            }
        },
        {
            name: 'stats',
            description: 'Show indexing statistics'
        },
        {
            name: 'test-rag',
            description: 'Generate test using RAG system (Markov walks + vector search)',
            params: {
                selection: {
                    description: 'Selected Java method code',
                    required: true
                }
            }
        }
    ],
    
    contextProviders: [
        {
            name: 'java-agent',
            description: 'Provides context from indexed Java projects via RAG',
            config: {
                serverUrl: 'http://localhost:8000',
                useRag: true,
                vectorSearch: true,
                markovWalks: true
            }
        }
    ]
};

