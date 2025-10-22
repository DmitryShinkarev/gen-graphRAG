/**
 * Slash command: /stats
 * Show project statistics
 */

import { apiClient } from '../api-client';

export async function statsCommand(): Promise<string> {
    try {
        const stats = await apiClient.getStats();

        const output = [
            '📊 Java Test Agent Statistics',
            '',
            `🔹 Methods in graph: ${stats.methods_in_graph}`,
            `🔹 Vectors stored: ${stats.vectors_stored}`,
            `🔹 Collection status: ${stats.collection_status}`,
            ''
        ];

        if (stats.methods_in_graph === 0) {
            output.push('💡 No projects indexed yet. Use /index to get started!');
        }

        return output.join('\n');

    } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return `❌ Failed to get statistics: ${errorMsg}`;
    }
}

