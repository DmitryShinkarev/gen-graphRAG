/**
 * Slash command: /test-rag
 * Generate unit test using RAG system (Markov walks + vector search)
 */

import { apiClient, TestGenerationResponse } from '../api-client';

export interface TestRagContext {
    input: string;
    selection?: string;
    filePath?: string;
}

/**
 * Extract method name and class name from Java code
 */
function parseJavaMethod(code: string): { methodName: string | null; className: string | null } {
    // Extract method name (public/private/protected Type methodName(...))
    const methodMatch = code.match(/(?:public|private|protected)?\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(/);
    
    // Extract class name from class declaration
    let classMatch = code.match(/class\s+(\w+)/);
    if (!classMatch) {
        // Try to extract from import or package context
        classMatch = code.match(/(?:public|private)?\s+class\s+(\w+)/);
    }
    
    return {
        methodName: methodMatch ? methodMatch[1] : null,
        className: classMatch ? classMatch[1] : null
    };
}

/**
 * Format test generation output for display
 */
function formatOutput(response: TestGenerationResponse, methodName: string): string {
    const output: string[] = [];
    
    output.push('✅ Test generated successfully using RAG system!');
    output.push('');
    output.push('📊 Details:');
    output.push(`  • Method: ${methodName}`);
    output.push(`  • Quality Score: ${response.quality_score.toFixed(1)}/100`);
    output.push(`  • Generation Time: ${response.duration.toFixed(2)}s`);
    output.push('');
    
    output.push('🔍 RAG Process Used:');
    output.push('  1. 🕸️  Markov walk on code graph (Memgraph)');
    output.push('  2. 🔍 Vector similarity search (Qdrant)');
    output.push('  3. 📚 Context gathering & ranking');
    output.push('  4. ✨ Test generation with full context');
    output.push('  5. 🔎 Quality evaluation');
    output.push('');
    
    if (response.suggestions && response.suggestions.length > 0) {
        output.push('💡 Suggestions for improvement:');
        response.suggestions.forEach((suggestion: string, idx: number) => {
            output.push(`  ${idx + 1}. ${suggestion}`);
        });
        output.push('');
    }
    
    output.push('📝 Generated Test Code:');
    output.push('```java');
    output.push(response.test_code);
    output.push('```');
    output.push('');
    
    const qualityEmoji = response.quality_score >= 90 ? '🌟' : 
                        response.quality_score >= 75 ? '✨' : 
                        response.quality_score >= 60 ? '👍' : '⚠️';
    
    output.push(`${qualityEmoji} Quality Assessment: ${response.quality_score.toFixed(1)}/100`);
    output.push('');
    output.push('💾 Next steps:');
    output.push('  • Copy the test code to your test directory');
    output.push('  • Review assertions and edge cases');
    output.push('  • Run tests to verify functionality');
    output.push('  • Address any suggestions if quality < 90');
    
    return output.join('\n');
}

/**
 * Format error message with helpful troubleshooting
 */
function formatError(error: Error, methodName?: string): string {
    const errorMsg = error.message;
    
    if (errorMsg.includes('404') || errorMsg.includes('not found')) {
        return '❌ Method not found in indexed project.\n\n' +
               '💡 Troubleshooting:\n' +
               '  1. Make sure project is indexed: /index [path]\n' +
               '  2. Check stats: /stats\n' +
               `  3. Verify method name is correct${methodName ? ` (looking for: ${methodName})` : ''}\n` +
               '  4. Re-index if you recently added the method';
    }
    
    if (errorMsg.includes('No response from API') || errorMsg.includes('ECONNREFUSED')) {
        return '❌ Cannot connect to API server.\n\n' +
               '💡 Start the backend:\n' +
               '  cd python\n' +
               '  source venv/bin/activate\n' +
               '  python api/server.py\n\n' +
               'The API should be running on http://localhost:8000';
    }
    
    if (errorMsg.includes('503') || errorMsg.includes('not initialized')) {
        return '❌ Test generation agents not ready.\n\n' +
               '💡 Check services:\n' +
               '  • docker-compose up -d (start databases)\n' +
               '  • Restart API server\n' +
               '  • Check logs: tail -f logs/agents.log';
    }
    
    return `❌ Test generation failed: ${errorMsg}\n\n` +
           `💡 Troubleshooting:\n` +
           `  • Check API health: curl http://localhost:8000/health\n` +
           `  • View logs: tail -f logs/agents.log\n` +
           `  • Verify project is indexed: /stats\n` +
           `  • Try re-indexing: /index [path]`;
}

export async function testRagCommand(context: TestRagContext): Promise<string> {
    const startTime = Date.now();
    
    try {
        // Get code to analyze
        const code = context.selection || context.input;
        
        if (!code || code.trim().length === 0) {
            return '❌ No code selected or provided.\n\n' +
                   '💡 Usage:\n' +
                   '  1. Select a Java method in your editor\n' +
                   '  2. Run: /test-rag\n' +
                   '  3. Get AI-generated test with RAG context!\n\n' +
                   '📖 Example:\n' +
                   '```java\n' +
                   'public int add(int a, int b) {\n' +
                   '    return a + b;\n' +
                   '}\n' +
                   '```';
        }
        
        // Parse method and class names
        const { methodName, className } = parseJavaMethod(code);
        
        if (!methodName) {
            return '❌ Could not extract method name from selection.\n\n' +
                   '💡 Make sure you selected a Java method with a clear signature:\n' +
                   '```java\n' +
                   'public ReturnType methodName(ParamType param) {\n' +
                   '    // method body\n' +
                   '}\n' +
                   '```\n\n' +
                   'Selected code:\n' +
                   '```\n' +
                   code.substring(0, 200) + (code.length > 200 ? '...' : '') + '\n' +
                   '```';
        }
        
        console.log(`📍 Found method: ${className ? className + '.' : ''}${methodName}()`);
        
        // Check API health first
        console.log('🔍 Checking API health...');
        const health = await apiClient.health();
        
        if (health.status !== 'healthy') {
            return `❌ API is not healthy. Status: ${health.status}\n\n` +
                   `💡 Components status:\n` +
                   `  • Graph: ${health.components.graph ? '✅' : '❌'}\n` +
                   `  • Embedder: ${health.components.embedder ? '✅' : '❌'}\n` +
                   `  • Vector Store: ${health.components.vector_store ? '✅' : '❌'}\n` +
                   `  • Indexer Agent: ${health.components.indexer_agent ? '✅' : '❌'}\n\n` +
                   `Please check your services:\n` +
                   `  docker-compose up -d\n` +
                   `  cd python && source venv/bin/activate && python api/server.py`;
        }
        
        // Show progress message
        console.log('🔍 Starting RAG-powered test generation...');
        console.log('  📚 Phase 1: Searching similar methods in vector DB (Qdrant)...');
        console.log('  🕸️  Phase 2: Walking code graph for dependencies (Memgraph)...');
        console.log('  🤖 Phase 3: Generating test with full context...');
        console.log('  🔎 Phase 4: Evaluating quality...');
        
        // Generate test using RAG
        const response = await apiClient.generateTest({
            target_method: methodName,
            class_name: className || undefined,
            file_path: context.filePath,
            project_id: 'default'
        });
        
        const totalDuration = (Date.now() - startTime) / 1000;
        console.log(`✅ Completed in ${totalDuration.toFixed(2)}s`);
        
        // Format and return output
        return formatOutput(response, methodName);
        
    } catch (error) {
        const errorObj = error instanceof Error ? error : new Error(String(error));
        return formatError(errorObj, undefined);
    }
}

