import { useState } from 'react';
import {
  ActivityIndicator,
  Keyboard,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { investor } from '@/api/client';
import { GuideLink } from '@/components/ui/GuideLink';
import { OwnerChecklistDrawer } from '@/components/investor/OwnerChecklistDrawer';
import { colors, font, radius, spacing } from '@/constants/theme';

export function OwnerInsights({ symbol }: { symbol: string }) {
  const qc = useQueryClient();
  const [nw, setNw] = useState('');
  const [checklistOpen, setChecklistOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['buffett-kit', symbol],
    queryFn: () => investor.buffettKit(symbol).then((r) => r.data),
    enabled: !!symbol,
  });

  const saveProfile = useMutation({
    mutationFn: () => investor.updateProfile({ net_worth_inr: parseFloat(nw) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portfolio-insights'] }),
  });

  if (isLoading) {
    return <ActivityIndicator color={colors.accent} style={{ marginVertical: spacing.md }} />;
  }
  if (!data) return null;

  const v = data.valuation;
  const q = data.quality;
  const b = data.benchmark;
  const verdictColor = v?.verdict === 'UNDERVALUED' ? colors.green : v?.verdict === 'OVERVALUED' ? colors.red : colors.yellow;
  const cl = data.owner_checklist ?? {};
  const checklistDone =
    cl.understand_business || cl.circle_of_competence || cl.comfortable_10y || cl.moat_rating || cl.management_rating;

  return (
    <View style={styles.wrap}>
      <View style={styles.titleRow}>
        <Text style={styles.title}>Owner investing · India</Text>
        <GuideLink section="owner-investing" label="Guide" guideVariant="stack" />
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Long-term fair value (DCF model)</Text>
        <Text style={styles.muted}>
          Graham band + DCF. Separate from AI agents below.
        </Text>
        {v?.fair_value_mid != null ? (
          <>
            <Text style={[styles.verdict, { color: verdictColor }]}>{v.verdict?.replace(/_/g, ' ')}</Text>
            <Text style={styles.row}>₹{v.fair_value_low} – ₹{v.fair_value_high} (mid ₹{v.fair_value_mid})</Text>
            <Text style={styles.muted}>Price ₹{v.current_price} · MoS {v.margin_of_safety_pct ?? '—'}%</Text>
          </>
        ) : (
          <Text style={styles.muted}>Refresh fundamentals for this NSE symbol</Text>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Quality {q?.grade}</Text>
        <Text style={styles.bigScore}>{q?.quality_score}/100</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>1Y vs Nifty & FD</Text>
        <Text style={styles.row}>Stock {b?.stock_return_pct ?? '—'}% · Nifty {b?.nifty_50_return_pct ?? '—'}% · FD ~{b?.fd_rate_pct}%</Text>
        {b?.notes?.map((n: string, i: number) => (
          <Text key={i} style={styles.muted}>• {n}</Text>
        ))}
      </View>

      <TouchableOpacity style={styles.checklistBtn} onPress={() => setChecklistOpen(true)}>
        <View style={styles.checklistBtnText}>
          <Text style={styles.checklistBtnTitle}>Owner checklist</Text>
          <Text style={styles.checklistBtnSub}>
            {checklistDone ? 'Your answers saved · tap to review' : 'Optional self-assessment · tap to open'}
          </Text>
        </View>
        <Text style={styles.chevron}>▸</Text>
      </TouchableOpacity>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Net worth (INR)</Text>
        <Text style={styles.muted}>Used for position % vs your wealth on Portfolio.</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. 5000000"
          placeholderTextColor={colors.textMuted}
          keyboardType={Platform.OS === 'ios' ? 'number-pad' : 'numeric'}
          value={nw}
          onChangeText={setNw}
          returnKeyType="done"
          blurOnSubmit
          onSubmitEditing={() => Keyboard.dismiss()}
        />
        {Platform.OS === 'android' && (
          <TouchableOpacity
            onPress={() => Keyboard.dismiss()}
            style={styles.dismissKb}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Text style={styles.dismissKbText}>Done</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          style={[styles.saveBtn, saveProfile.isPending && styles.saveBtnDisabled]}
          onPress={() => saveProfile.mutate()}
          disabled={saveProfile.isPending || !nw.trim()}
        >
          <Text style={styles.saveBtnText}>{saveProfile.isPending ? 'Saving…' : 'Save net worth'}</Text>
        </TouchableOpacity>
      </View>

      <OwnerChecklistDrawer
        symbol={symbol}
        visible={checklistOpen}
        onClose={() => setChecklistOpen(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: spacing.lg, zIndex: 1, elevation: 2 },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  title: { fontSize: font.xs, fontWeight: '700', color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.8, flex: 1 },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  cardTitle: { fontSize: font.sm, fontWeight: '700', color: colors.textPrimary },
  verdict: { fontSize: font.lg, fontWeight: '800', marginTop: 4 },
  bigScore: { fontSize: font.xxl, fontWeight: '900', color: colors.accent, marginTop: 4 },
  row: { fontSize: font.sm, color: colors.textSecondary, marginTop: 4 },
  muted: { fontSize: font.xs, color: colors.textMuted, marginTop: 4, lineHeight: 18 },
  checklistBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.sm,
    gap: spacing.sm,
  },
  checklistBtnText: { flex: 1, minWidth: 0 },
  checklistBtnTitle: { fontSize: font.sm, fontWeight: '700', color: colors.textPrimary },
  checklistBtnSub: { fontSize: font.xs, color: colors.textMuted, marginTop: 2 },
  chevron: { fontSize: 18, color: colors.accent, fontWeight: '700' },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.sm,
    color: colors.textPrimary,
    marginTop: 8,
    fontSize: font.sm,
  },
  saveBtn: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 10,
    minHeight: 44,
  },
  saveBtnDisabled: { opacity: 0.5 },
  saveBtnText: { color: '#fff', fontWeight: '700', fontSize: font.sm },
  dismissKb: { alignSelf: 'flex-end', marginTop: 6 },
  dismissKbText: { fontSize: font.sm, fontWeight: '600', color: colors.accent },
});
