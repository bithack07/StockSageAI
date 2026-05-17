import { useState } from 'react';
import {
  ActivityIndicator, FlatList, RefreshControl, StyleSheet,
  Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { watchlist } from '@/api/client';
import { SymbolLabel } from '@/components/ui/SymbolLabel';
import { canonicalForNav } from '@/lib/symbolDisplay';
import { colors, font, radius, spacing } from '@/constants/theme';

const DIR_COLOR: Record<string, string> = {
  BULLISH: colors.green,
  BEARISH: colors.red,
  NEUTRAL: colors.yellow,
};

export default function WatchlistScreen() {
  const qc = useQueryClient();
  const [newSymbol, setNewSymbol] = useState('');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => watchlist.get().then((r) => r.data),
  });

  const addMutation = useMutation({
    mutationFn: () => watchlist.add(newSymbol.trim()),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['watchlist'] }); setNewSymbol(''); },
  });

  const refreshMutation = useMutation({
    mutationFn: () => watchlist.refreshPreanalysis(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => watchlist.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  return (
    <View style={styles.container}>
      <Text style={styles.tip}>
        INFY and INFY.NS are the same stock — we store one NSE ticker per company.
      </Text>

      <View style={styles.addRow}>
        <TextInput
          style={styles.input}
          placeholder="Add Infosys, INFY, TCS…"
          placeholderTextColor={colors.textMuted}
          value={newSymbol}
          onChangeText={setNewSymbol}
          autoCapitalize="characters"
          onSubmitEditing={() => newSymbol.trim() && addMutation.mutate()}
          returnKeyType="done"
        />
        <TouchableOpacity
          style={[styles.addBtn, (!newSymbol.trim() || addMutation.isPending) && styles.addBtnDisabled]}
          onPress={() => addMutation.mutate()}
          disabled={!newSymbol.trim() || addMutation.isPending}
        >
          <Text style={styles.addBtnText}>{addMutation.isPending ? '…' : '+ Add'}</Text>
        </TouchableOpacity>
      </View>

      {(data?.length ?? 0) > 0 && (
        <TouchableOpacity style={styles.refreshBtn} onPress={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}>
          <Text style={styles.refreshText}>{refreshMutation.isPending ? 'Queuing…' : 'Refresh all AI analysis'}</Text>
        </TouchableOpacity>
      )}

      <FlatList
        data={data ?? []}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={isLoading} onRefresh={refetch} tintColor={colors.accent} />}
        renderItem={({ item }) => {
          const preview = item.preview;
          const dir = preview?.direction;
          return (
            <TouchableOpacity style={styles.row} onPress={() => router.push(`/stock/${canonicalForNav(item)}`)}>
              <View style={styles.rowLeft}>
                <SymbolLabel item={item} showStoredHint />
                <View style={styles.metaRow}>
                  {item.price != null && (
                    <Text style={styles.price}>₹{Number(item.price).toLocaleString('en-IN')}</Text>
                  )}
                  {dir && (
                    <Text style={[styles.dir, { color: DIR_COLOR[dir] ?? colors.textSecondary }]}>
                      {dir} · {preview.confidence_pct ?? '—'}%
                    </Text>
                  )}
                  {preview?.status === 'pending' && (
                    <Text style={styles.pending}>AI queued…</Text>
                  )}
                </View>
              </View>
              <TouchableOpacity onPress={() => removeMutation.mutate(item.id)} style={styles.removeBtn}>
                <Text style={styles.removeBtnText}>Remove</Text>
              </TouchableOpacity>
            </TouchableOpacity>
          );
        }}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        contentContainerStyle={{ paddingBottom: 32 }}
        ListEmptyComponent={
          !isLoading ? <Text style={styles.empty}>Your watchlist is empty.</Text> : null
        }
      />
      {isLoading && <ActivityIndicator color={colors.accent} style={{ marginTop: 24 }} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  tip: { fontSize: font.xs, color: colors.textMuted, marginBottom: spacing.sm, lineHeight: 18 },
  addRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.sm },
  input: {
    flex: 1, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border,
    borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: 13,
    color: colors.textPrimary, fontSize: font.md,
  },
  addBtn: { backgroundColor: colors.accent, borderRadius: radius.md, paddingHorizontal: 16, justifyContent: 'center' },
  addBtnDisabled: { opacity: 0.4 },
  addBtnText: { color: '#fff', fontWeight: '700', fontSize: font.sm },
  refreshBtn: { alignSelf: 'flex-start', marginBottom: spacing.md },
  refreshText: { fontSize: font.sm, fontWeight: '600', color: colors.accent },
  row: {
    flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between',
    paddingVertical: 14,
  },
  rowLeft: { flex: 1, paddingRight: spacing.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8, alignItems: 'center' },
  price: { fontSize: font.sm, fontWeight: '700', color: colors.textPrimary },
  dir: { fontSize: font.xs, fontWeight: '700' },
  pending: { fontSize: font.xs, color: colors.accent },
  separator: { height: 1, backgroundColor: colors.border },
  removeBtn: {
    backgroundColor: colors.redDim, borderRadius: radius.sm,
    paddingHorizontal: 10, paddingVertical: 5,
  },
  removeBtnText: { color: colors.red, fontSize: font.xs, fontWeight: '700' },
  empty: { color: colors.textMuted, textAlign: 'center', marginTop: 40, fontSize: font.md },
});
