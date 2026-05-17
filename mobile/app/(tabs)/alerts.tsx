import { useState } from 'react';
import {
  ActivityIndicator, FlatList, Modal, RefreshControl,
  StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alerts } from '@/api/client';
import { colors, font, radius, spacing } from '@/constants/theme';

const CONDITIONS = [
  { label: 'Price ↑ Above', value: 'price_above' },
  { label: 'Price ↓ Below', value: 'price_below' },
  { label: 'RSI ↑', value: 'rsi_above' },
  { label: 'RSI ↓', value: 'rsi_below' },
  { label: 'MACD X', value: 'macd_crossover' },
];

export default function AlertsScreen() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ symbol: '', condition: 'price_above', threshold: '' });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => alerts.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: () => alerts.create({
      symbol: form.symbol.toUpperCase(),
      condition: form.condition,
      threshold: parseFloat(form.threshold) || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] });
      setShowCreate(false);
      setForm({ symbol: '', condition: 'price_above', threshold: '' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => alerts.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  });

  return (
    <View style={styles.container}>
      <TouchableOpacity style={styles.createBtn} onPress={() => setShowCreate(true)}>
        <Text style={styles.createBtnText}>+ New Alert</Text>
      </TouchableOpacity>

      <FlatList
        data={data ?? []}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={isLoading} onRefresh={refetch} tintColor={colors.accent} />}
        renderItem={({ item }) => (
          <View style={[styles.alertCard, !item.is_active && styles.alertInactive]}>
            <View style={styles.alertLeft}>
              <Text style={styles.alertSymbol}>{item.symbol}</Text>
              <View style={styles.condBadge}>
                <Text style={styles.condBadgeText}>{item.condition.replace(/_/g, ' ')}</Text>
              </View>
              {item.threshold != null && (
                <Text style={styles.alertThreshold}>@ ₹{item.threshold}</Text>
              )}
            </View>
            <View style={styles.alertRight}>
              <View style={[styles.statusDot, { backgroundColor: item.is_active ? colors.green : colors.textMuted }]} />
              {item.is_active && (
                <TouchableOpacity onPress={() => deleteMutation.mutate(item.id)} style={styles.deleteBtn}>
                  <Text style={styles.deleteBtnText}>Delete</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        )}
        ItemSeparatorComponent={() => <View style={{ height: 8 }} />}
        contentContainerStyle={{ paddingBottom: 32 }}
        ListEmptyComponent={!isLoading ? <Text style={styles.empty}>No alerts yet.</Text> : null}
      />
      {isLoading && <ActivityIndicator color={colors.accent} style={{ marginTop: 24 }} />}

      {/* Create Modal */}
      <Modal visible={showCreate} transparent animationType="slide">
        <View style={styles.overlay}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>New Alert</Text>

            <TextInput
              style={styles.input}
              placeholder="Symbol (e.g. HDFC.NS)"
              placeholderTextColor={colors.textMuted}
              value={form.symbol}
              onChangeText={(v) => setForm((f) => ({ ...f, symbol: v }))}
              autoCapitalize="characters"
            />

            <View style={styles.condRow}>
              {CONDITIONS.map((c) => (
                <TouchableOpacity
                  key={c.value}
                  style={[styles.condChip, form.condition === c.value && styles.condChipActive]}
                  onPress={() => setForm((f) => ({ ...f, condition: c.value }))}
                >
                  <Text style={[styles.condChipText, form.condition === c.value && styles.condChipTextActive]}>
                    {c.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <TextInput
              style={styles.input}
              placeholder="Threshold value"
              placeholderTextColor={colors.textMuted}
              value={form.threshold}
              onChangeText={(v) => setForm((f) => ({ ...f, threshold: v }))}
              keyboardType="numeric"
            />

            <View style={styles.modalActions}>
              <TouchableOpacity onPress={() => setShowCreate(false)} style={styles.cancelBtn}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => createMutation.mutate()}
                style={[styles.confirmBtn, createMutation.isPending && styles.confirmBtnDisabled]}
                disabled={createMutation.isPending}
              >
                <Text style={styles.confirmBtnText}>{createMutation.isPending ? 'Creating…' : 'Create'}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  createBtn: { backgroundColor: colors.accent, borderRadius: radius.md, paddingVertical: 14, alignItems: 'center', marginBottom: spacing.md },
  createBtnText: { color: '#fff', fontWeight: '700', fontSize: font.md },
  alertCard: {
    backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border,
    borderRadius: radius.lg, padding: spacing.md,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  alertInactive: { opacity: 0.45 },
  alertLeft: { flex: 1, gap: 5 },
  alertSymbol: { fontSize: font.md, fontWeight: '700', color: colors.textPrimary },
  condBadge: { alignSelf: 'flex-start', backgroundColor: colors.accentDim, borderRadius: radius.sm, paddingHorizontal: 8, paddingVertical: 3 },
  condBadgeText: { fontSize: font.xs, fontWeight: '700', color: colors.accent, textTransform: 'capitalize' },
  alertThreshold: { fontSize: font.sm, color: colors.textSecondary },
  alertRight: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  deleteBtn: { backgroundColor: colors.redDim, borderRadius: radius.sm, paddingHorizontal: 10, paddingVertical: 5 },
  deleteBtnText: { color: colors.red, fontSize: font.xs, fontWeight: '700' },
  empty: { color: colors.textMuted, textAlign: 'center', marginTop: 40, fontSize: font.md },
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.6)' },
  modal: {
    backgroundColor: colors.card, borderTopLeftRadius: radius.xl, borderTopRightRadius: radius.xl,
    padding: spacing.lg, gap: spacing.md,
    borderWidth: 1, borderBottomWidth: 0, borderColor: colors.border,
  },
  modalTitle: { fontSize: font.xl, fontWeight: '700', color: colors.textPrimary },
  input: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: radius.md, padding: 14, color: colors.textPrimary, fontSize: font.md,
  },
  condRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  condChip: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.full, paddingHorizontal: 12, paddingVertical: 7 },
  condChipActive: { backgroundColor: colors.accentDim, borderColor: colors.accent },
  condChipText: { color: colors.textMuted, fontSize: font.sm, fontWeight: '600' },
  condChipTextActive: { color: colors.accent },
  modalActions: { flexDirection: 'row', gap: spacing.sm },
  cancelBtn: { flex: 1, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingVertical: 14, alignItems: 'center' },
  cancelBtnText: { color: colors.textSecondary, fontWeight: '600' },
  confirmBtn: { flex: 1, backgroundColor: colors.accent, borderRadius: radius.md, paddingVertical: 14, alignItems: 'center' },
  confirmBtnDisabled: { opacity: 0.5 },
  confirmBtnText: { color: '#fff', fontWeight: '700' },
});
