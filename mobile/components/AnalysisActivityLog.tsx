import { ScrollView, StyleSheet, Text, View } from 'react-native';
import type { ActivityStep, StepStatus } from '@/lib/analysisLog';
import { useAnalysisStore } from '@/store/analysisStore';
import { colors, font, radius, spacing } from '@/constants/theme';

const STATUS_ICON: Record<StepStatus, string> = {
  info: '○',
  running: '◐',
  done: '✓',
  error: '✕',
};

const STATUS_COLOR: Record<StepStatus, string> = {
  info: colors.textMuted,
  running: colors.accent,
  done: colors.green,
  error: colors.red,
};

const AGENT_COLOR: Record<string, string> = {
  fundamental: '#a78bfa',
  technical: '#34d399',
  sentiment: '#fbbf24',
  ml: '#60a5fa',
  orchestrator: '#f472b6',
  system: colors.textMuted,
};

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function LogRow({ step, showPhase }: { step: ActivityStep; showPhase: boolean }) {
  const status = step.status ?? 'info';
  const agentColor = AGENT_COLOR[step.agent ?? 'system'] ?? colors.accent;

  return (
    <View>
      {showPhase && step.phaseLabel && (
        <Text style={styles.phaseHeader}>{step.phaseLabel}</Text>
      )}
      <View style={[styles.row, status === 'running' && styles.rowActive]}>
        <Text style={[styles.statusIcon, { color: STATUS_COLOR[status] }]}>{STATUS_ICON[status]}</Text>
        <Text style={styles.time}>{formatTime(step.timestamp)}</Text>
        <Text style={[styles.agent, { color: agentColor }]} numberOfLines={1}>
          {step.agentLabel ?? step.agent}
        </Text>
        <Text style={styles.message}>{step.message}</Text>
      </View>
      {step.detail ? <Text style={styles.detail}>{step.detail}</Text> : null}
    </View>
  );
}

export function AnalysisActivityLog() {
  const { activitySteps, isAnalysing, agentOutputs } = useAnalysisStore();

  if (activitySteps.length === 0 && Object.keys(agentOutputs).length === 0) {
    return (
      <Text style={styles.placeholder}>
        {isAnalysing ? 'Waiting for analysis steps…' : 'Open a stock to see step-by-step activity here.'}
      </Text>
    );
  }

  let lastPhase = '';

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Activity log</Text>
        {isAnalysing && (
          <View style={styles.liveBadge}>
            <Text style={styles.liveText}>Live</Text>
          </View>
        )}
      </View>

      <ScrollView
        style={styles.logScroll}
        contentContainerStyle={styles.logBody}
        nestedScrollEnabled
        showsVerticalScrollIndicator
        keyboardShouldPersistTaps="handled"
      >
        {activitySteps.map((step) => {
          const showPhase = !!(step.phaseLabel && step.phaseLabel !== lastPhase);
          if (showPhase) lastPhase = step.phaseLabel ?? '';
          return <LogRow key={step.id} step={step} showPhase={showPhase} />;
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm },
  title: {
    fontSize: font.xs,
    fontWeight: '800',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  liveBadge: {
    backgroundColor: colors.accentDim,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: radius.full,
  },
  liveText: { fontSize: 10, fontWeight: '700', color: colors.accent },
  logScroll: { maxHeight: 280 },
  logBody: { paddingBottom: spacing.xs },
  placeholder: { fontSize: font.sm, color: colors.textMuted, fontStyle: 'italic', marginBottom: spacing.md },
  phaseHeader: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginTop: spacing.sm,
    marginBottom: 4,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    paddingVertical: 5,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowActive: {
    backgroundColor: 'rgba(59, 130, 246, 0.06)',
    borderRadius: radius.sm,
    paddingHorizontal: 4,
  },
  statusIcon: { width: 12, fontSize: 11, fontWeight: '700' },
  time: { width: 58, fontSize: 10, color: colors.textMuted, fontVariant: ['tabular-nums'] },
  agent: { width: 72, fontSize: 10, fontWeight: '700' },
  message: { flex: 1, flexShrink: 1, minWidth: 0, fontSize: font.xs, color: colors.textSecondary, lineHeight: 18 },
  detail: { fontSize: 10, color: colors.textMuted, marginLeft: 88, marginBottom: 4, lineHeight: 14 },
});
