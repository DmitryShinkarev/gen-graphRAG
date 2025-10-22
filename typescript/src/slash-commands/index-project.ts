/**
 * Slash command: /index
 * Index a Java project for test generation
 */

import { apiClient } from '../api-client';
import * as path from 'path';

export interface SlashCommandContext {
    input: string;
    workspacePath: string;
}

export async function indexProjectCommand(context: SlashCommandContext): Promise<string> {
    try {
        // Determine project path
        const projectPath = context.input.trim() || context.workspacePath;
        
        if (!projectPath) {
            return '❌ No project path provided. Usage: /index [path]';
        }

        // Resolve absolute path
        const absolutePath = path.resolve(projectPath);
        
        console.log(`Starting indexing for: ${absolutePath}`);
        
        // Check health first
        const health = await apiClient.health();
        if (health.status !== 'healthy') {
            return `❌ API is not healthy. Status: ${health.status}`;
        }

        // Index project
        const result = await apiClient.indexProject({
            project_path: absolutePath,
            force: false
        });

        // Format response
        const output = [
            '✅ Project indexed successfully!',
            '',
            `📊 Statistics:`,
            `  • Files indexed: ${result.indexed_files}`,
            `  • Classes parsed: ${result.parsed_classes}`,
            `  • Methods found: ${result.methods_count}`,
            `  • Duration: ${result.duration.toFixed(2)}s`,
            ''
        ];

        if (result.errors.length > 0) {
            output.push('⚠️  Warnings:');
            result.errors.forEach(err => output.push(`  • ${err}`));
            output.push('');
        }

        output.push('🎯 Next steps:');
        output.push('  • Use /stats to see project statistics');
        output.push('  • Select a Java method and ask to generate tests');

        return output.join('\n');

    } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return `❌ Indexing failed: ${errorMsg}\n\n` +
               `💡 Make sure:\n` +
               `  • FastAPI server is running (python -m api.server)\n` +
               `  • Docker services are up (docker-compose up -d)\n` +
               `  • Project path is correct`;
    }
}

