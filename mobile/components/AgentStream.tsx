import { StyleSheet, Text, View } from 'react-native';
import { useAnalysisStore } from '@/store/analysisStore';
import { AnalysisActivityLog } from '@/components/AnalysisActivityLog';
import { colors, font, radius, spacing } from '@/constants/theme';

const AGENT_COLORS: Record<string, string> = {
  fundamental: '#a78bfa',
  technical: '#34d399',
  sentiment: '#fbbf24',
  ml: '#60a5fa',
};

function signalFromOutput(output: Record<string, unknown>): string | null {
  if ('signal' in output) return String(output.signal);
  if ('valuation_verdict' in output) return String(output.valuation_verdict);
  if ('sentiment_signal' in output) return String(output.sentiment_signal);
  if ('bullish_prob' in output) {
    const bull = `Dir ${Math.round(Number(output.bullish_prob) * 100)}%`;
    const lstm = output.lstm as { up_prob?: number; direction?: string } | undefined;
    if (lstm?.up_prob != null) {
      return `${bull} · LSTM ${lstm.direction ?? ''} ${Math.round(lstm.up_prob * 100)}%`.trim();
    }
    return bull;
  }
  return null;
}

/** Agent result tiles + full step-by-step activity log. */
export function AgentStream() {
  const { agentOutputs } = useAnalysisStore();
  const hasTiles = Object.keys(agentOutputs).length > 0;

  return (
    <View style={styles.container}>
      {hasTiles && (
        <View style={styles.grid}>
          {Object.entries(agentOutputs).map(([agent, output]) => {
            const out = output as Record<string, unknown>;
            const sig = output && typeof output === 'object' ? signalFromOutput(out) : null;
            const err = typeof out?.error === 'string' ? out.error : typeof out?.llm_error === 'string' ? out.llm_error : null;
            const color = AGENT_COLORS[agent] ?? colors.textSecondary;
            return (
              <View key={agent} style={[styles.tile, { borderLeftColor: color }]}>
                <Text style={[styles.agentName, { color }]}>{agent.toUpperCase()}</Text>
                {sig ? <Text style={styles.signal}>{sig}</Text> : null}
                {err ? <Text style={styles.agentNote} numberOfLines={2}>Used fallback indicators</Text> : null}
              </View>
            );
          })}
        </View>
      )}
      <AnalysisActivityLog />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.sm },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  tile: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    borderLeftWidth: 3,
    padding: spacing.md,
  },
  agentName: { fontSize: font.xs, fontWeight: '800', letterSpacing: 0.6, marginBottom: 4 },
  signal: { fontSize: font.sm, fontWeight: '600', color: colors.textPrimary },
  agentNote: { fontSize: font.xs, color: colors.textMuted, marginTop: 4 },
});
