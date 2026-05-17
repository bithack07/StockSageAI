import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { investor } from '@/api/client';
import { GuideLink } from '@/components/ui/GuideLink';
import { colors, font, radius, spacing } from '@/constants/theme';

const THESIS_FIELDS = [
  { key: 'thesis_text', label: 'Why I bought', lines: 2 },
  { key: 'moat_notes', label: 'Competitive moat', lines: 2 },
  { key: 'management_notes', label: 'Management & governance', lines: 2 },
  { key: 'ten_year_thesis', label: '10-year thesis', lines: 3 },
] as const;

interface Props {
  holdingId: string;
  symbol: string;
  collapsed?: boolean;
  onToggle?: () => void;
  /** When false, header is not tappable (e.g. always open on analysis screen). */
  collapsible?: boolean;
}

export function HoldingThesisCard({
  holdingId,
  symbol,
  collapsed = true,
  onToggle,
  collapsible = true,
}: Props) {
  const qc = useQueryClient();
  const [fields, setFields] = useState<Record<string, string>>({});

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['thesis', holdingId],
    queryFn: () => investor.getThesis(holdingId).then((r) => r.data),
    enabled: !!holdingId,
  });

  const thesis = data?.thesis;

  useEffect(() => {
    if (!thesis) return;
    setFields({
      thesis_text: thesis.thesis_text ?? '',
      moat_notes: thesis.moat_notes ?? '',
      management_notes: thesis.management_notes ?? '',
      ten_year_thesis: thesis.ten_year_thesis ?? '',
    });
  }, [holdingId, thesis?.thesis_text, thesis?.moat_notes, thesis?.management_notes, thesis?.ten_year_thesis]);

  const saveMutation = useMutation({
    mutationFn: () => investor.saveThesis(holdingId, fields),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['thesis', holdingId] }),
    onError: () => {
      Alert.alert('Could not save thesis', 'Check your connection and try again.');
    },
  });

  const hasContent = THESIS_FIELDS.some((f) => (fields[f.key] ?? '').trim().length > 0);

  const showBody = !collapsible || !collapsed;
  const HeaderWrapper = collapsible ? TouchableOpacity : View;

  return (
    <View style={[styles.wrap, !collapsible && styles.wrapCard]}>
      <HeaderWrapper
        style={styles.header}
        onPress={collapsible ? onToggle : undefined}
        activeOpacity={collapsible ? 0.8 : 1}
      >
        <Text style={styles.headerTitle}>Investment thesis</Text>
        <Text style={styles.headerHint}>
          {collapsible
            ? collapsed
              ? hasContent
                ? 'Notes saved · tap to edit'
                : 'Tap to add why you own this'
              : 'Tap to collapse'
            : 'Your notes for this holding'}
        </Text>
        {collapsible ? <Text style={styles.chevron}>{collapsed ? '▸' : '▾'}</Text> : null}
      </HeaderWrapper>

      {showBody && (
        <View style={styles.body}>
          <GuideLink section="owner-investing" label="What is an investment thesis?" />
          {isError ? (
            <TouchableOpacity onPress={() => refetch()}>
              <Text style={styles.errorText}>Could not load thesis. Tap to retry.</Text>
            </TouchableOpacity>
          ) : isLoading ? (
            <ActivityIndicator color={colors.accent} style={{ marginVertical: spacing.sm }} />
          ) : (
            <>
              {THESIS_FIELDS.map(({ key, label, lines }) => (
                <View key={key} style={styles.field}>
                  <Text style={styles.label}>{label}</Text>
                  <TextInput
                    style={[styles.input, lines > 2 && styles.inputTall]}
                    value={fields[key] ?? ''}
                    onChangeText={(v) => setFields((p) => ({ ...p, [key]: v }))}
                    placeholder={`${label} for ${symbol.replace(/\.(NS|BO)$/i, '')}`}
                    placeholderTextColor={colors.textMuted}
                    multiline
                    numberOfLines={lines}
                    textAlignVertical="top"
                  />
                </View>
              ))}
              <TouchableOpacity
                style={[styles.saveBtn, saveMutation.isPending && styles.saveBtnDisabled]}
                onPress={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
              >
                <Text style={styles.saveBtnText}>
                  {saveMutation.isPending ? 'Saving…' : 'Save thesis'}
                </Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.sm,
  },
  wrapCard: {
    marginTop: 0,
    marginBottom: spacing.sm,
    borderTopWidth: 0,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
  },
  errorText: { fontSize: font.sm, color: colors.red, marginVertical: spacing.sm },
  header: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', minHeight: 40 },
  headerTitle: { fontSize: font.sm, fontWeight: '700', color: colors.textPrimary, marginRight: 8 },
  headerHint: { flex: 1, fontSize: font.xs, color: colors.textMuted },
  chevron: { fontSize: 16, color: colors.accent, fontWeight: '700', marginLeft: 4 },
  body: { marginTop: spacing.sm },
  field: { marginBottom: spacing.sm },
  label: { fontSize: font.xs, fontWeight: '600', color: colors.textMuted, marginBottom: 4 },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.sm,
    color: colors.textPrimary,
    fontSize: font.sm,
    minHeight: 44,
  },
  inputTall: { minHeight: 72 },
  saveBtn: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 12,
    alignItems: 'center',
    minHeight: 44,
    marginTop: spacing.xs,
  },
  saveBtnDisabled: { opacity: 0.6 },
  saveBtnText: { color: '#fff', fontWeight: '700', fontSize: font.sm },
});
