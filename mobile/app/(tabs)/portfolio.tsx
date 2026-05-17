import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Keyboard,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { portfolio } from '@/api/client';
import { PortfolioInsights } from '@/components/investor/PortfolioInsights';
import { EmptyState } from '@/components/ui/EmptyState';
import { GuideLink } from '@/components/ui/GuideLink';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { SymbolSuggestionDrawer } from '@/components/ui/SymbolSuggestionDrawer';
import { HoldingThesisCard } from '@/components/investor/HoldingThesisCard';
import { colors, font, radius, spacing } from '@/constants/theme';
import { formatInr, formatPct, safeNum } from '@/lib/formatInr';
import { canonicalForNav } from '@/lib/symbolDisplay';

interface Holding {
  id: string;
  symbol: string;
  quantity: number;
  avg_buy_price: number;
  current_price: number;
  invested_value?: number;
  current_value?: number;
  pnl: number;
  pnl_pct: number;
  buy_date?: string | null;
}

interface PortfolioData {
  holdings: Holding[];
  total_invested?: number;
  total_current_value?: number;
  total_pnl?: number;
  total_pnl_pct?: number;
  portfolio?: null;
}

function normalizePortfolio(raw: PortfolioData | undefined): PortfolioData {
  if (!raw) {
    return { holdings: [], total_invested: 0, total_current_value: 0, total_pnl: 0, total_pnl_pct: 0 };
  }
  if (raw.portfolio === null && raw.total_invested == null) {
    return {
      ...raw,
      holdings: raw.holdings ?? [],
      total_invested: 0,
      total_current_value: 0,
      total_pnl: 0,
      total_pnl_pct: 0,
    };
  }
  return { ...raw, holdings: raw.holdings ?? [] };
}

function holdingInvested(h: Holding): number {
  return h.invested_value ?? safeNum(h.quantity) * safeNum(h.avg_buy_price);
}

function holdingCurrent(h: Holding): number {
  return h.current_value ?? safeNum(h.quantity) * safeNum(h.current_price);
}

export default function PortfolioScreen() {
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [symbolFocused, setSymbolFocused] = useState(false);
  const [form, setForm] = useState({ symbol: '', quantity: '', avg_buy_price: '' });
  const [expandedThesisId, setExpandedThesisId] = useState<string | null>(null);

  const { data: rawData, isLoading, isFetching, refetch, isError } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => portfolio.get().then((r) => r.data as PortfolioData),
    staleTime: 5 * 60_000,
  });

  const data = normalizePortfolio(rawData);
  const holdings = data.holdings;
  const totalPnl = safeNum(data.total_pnl);
  const pnlPositive = totalPnl >= 0;

  const addMutation = useMutation({
    mutationFn: () =>
      portfolio.addHolding({
        symbol: form.symbol.trim().toUpperCase(),
        quantity: parseFloat(form.quantity),
        avg_buy_price: parseFloat(form.avg_buy_price),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio-insights'] });
      setShowAdd(false);
      setSymbolFocused(false);
      setForm({ symbol: '', quantity: '', avg_buy_price: '' });
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      const detail = e?.response?.data?.detail;
      Alert.alert('Could not add', typeof detail === 'string' ? detail : 'Check symbol and values.');
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => portfolio.removeHolding(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio-insights'] });
    },
    onError: () => Alert.alert('Remove failed', 'Could not remove this holding. Try again.'),
  });

  const confirmRemove = useCallback(
    (item: Holding) => {
      Alert.alert('Remove holding', `Remove ${item.symbol} from your portfolio?`, [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: () => removeMutation.mutate(item.id),
        },
      ]);
    },
    [removeMutation],
  );

  const renderHolding = useCallback(
    ({ item }: { item: Holding }) => {
      const invested = holdingInvested(item);
      const current = holdingCurrent(item);
      const pnl = safeNum(item.pnl, current - invested);
      const pnlPct = safeNum(item.pnl_pct, invested > 0 ? (pnl / invested) * 100 : 0);
      const pos = pnl >= 0;
      const navSymbol = canonicalForNav({ symbol: item.symbol, canonical_symbol: item.symbol });

      return (
        <View style={styles.holdingCard}>
          <View style={styles.holdingTop}>
            <TouchableOpacity
              style={styles.holdingMain}
              onPress={() => router.push(`/stock/${navSymbol}`)}
              activeOpacity={0.75}
            >
              <Text style={styles.holdingSymbol}>{item.symbol.replace(/\.(NS|BO)$/i, '')}</Text>
              <Text style={styles.holdingMeta}>
                {safeNum(item.quantity)} shares · avg {formatInr(item.avg_buy_price)}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => confirmRemove(item)}
              style={styles.removeBtn}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Text style={styles.removeBtnText}>Remove</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            onPress={() => router.push(`/stock/${navSymbol}`)}
            activeOpacity={0.75}
          >
            <View style={styles.statsGrid}>
              <View style={styles.statCell}>
                <Text style={styles.statLabel}>Invested</Text>
                <Text style={styles.statValue}>{formatInr(invested)}</Text>
              </View>
              <View style={styles.statCell}>
                <Text style={styles.statLabel}>Current</Text>
                <Text style={styles.statValue}>{formatInr(current)}</Text>
              </View>
              <View style={styles.statCell}>
                <Text style={styles.statLabel}>Price</Text>
                <Text style={styles.statValue}>{formatInr(item.current_price)}</Text>
              </View>
              <View style={styles.statCell}>
                <Text style={styles.statLabel}>P&L</Text>
                <Text style={[styles.statValue, { color: pos ? colors.green : colors.red }]}>
                  {pnl >= 0 ? '+' : ''}{formatInr(pnl, 0)} ({formatPct(pnlPct)})
                </Text>
              </View>
            </View>
          </TouchableOpacity>

          <HoldingThesisCard
            holdingId={item.id}
            symbol={item.symbol}
            collapsed={expandedThesisId !== item.id}
            onToggle={() =>
              setExpandedThesisId((id) => (id === item.id ? null : item.id))
            }
          />
        </View>
      );
    },
    [confirmRemove, expandedThesisId],
  );

  const listHeader = (
    <>
      <PortfolioInsights />
      <GuideLink section="portfolio" label="What do P&L and allocation mean?" />

      <View style={styles.summaryCard}>
        <Text style={styles.summaryTitle}>Portfolio summary</Text>
        <View style={styles.summaryRow}>
          <View style={styles.summaryCell}>
            <Text style={styles.summaryLabel}>Invested</Text>
            <Text style={styles.summaryValue}>{formatInr(data.total_invested, 0)}</Text>
          </View>
          <View style={styles.summaryCell}>
            <Text style={styles.summaryLabel}>Current</Text>
            <Text style={styles.summaryValue}>{formatInr(data.total_current_value, 0)}</Text>
          </View>
        </View>
        <Text style={[styles.summaryPnl, { color: pnlPositive ? colors.green : colors.red }]}>
          {totalPnl >= 0 ? '+' : ''}{formatInr(totalPnl)} ({formatPct(data.total_pnl_pct)})
        </Text>
      </View>

      <TouchableOpacity style={styles.addBtn} onPress={() => setShowAdd(true)}>
        <Text style={styles.addBtnText}>+ Add holding</Text>
      </TouchableOpacity>

      {isError && (
        <Text style={styles.errorText}>Could not load portfolio. Pull down to retry.</Text>
      )}

      <SectionHeader title="Holdings" />
    </>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={holdings}
        keyExtractor={(item) => item.id}
        renderItem={renderHolding}
        ListHeaderComponent={listHeader}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              icon="◇"
              title="No holdings yet"
              description="Tap + Add holding to track shares, cost basis, and live P&L."
            />
          ) : null
        }
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        contentContainerStyle={{
          padding: spacing.md,
          paddingBottom: Math.max(insets.bottom, spacing.md) + 72,
        }}
        refreshControl={
          <RefreshControl
            refreshing={isFetching && !isLoading}
            onRefresh={() => {
              refetch();
              queryClient.invalidateQueries({ queryKey: ['portfolio-insights'] });
            }}
            tintColor={colors.accent}
          />
        }
        showsVerticalScrollIndicator={false}
      />

      {isLoading && (
        <ActivityIndicator color={colors.accent} style={styles.loader} size="large" />
      )}

      <Modal visible={showAdd} transparent animationType="slide" onRequestClose={() => setShowAdd(false)}>
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          keyboardVerticalOffset={Platform.OS === 'ios' ? 8 : 0}
        >
          <Pressable
            style={styles.modalBackdrop}
            onPress={() => { Keyboard.dismiss(); setSymbolFocused(false); setShowAdd(false); }}
          />
          <ScrollView
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
            bounces={false}
            contentContainerStyle={styles.modalScrollContent}
          >
            <View style={[styles.modal, { paddingBottom: Math.max(insets.bottom, spacing.lg) }]}>
              <Text style={styles.modalTitle}>Add holding</Text>
              <Text style={styles.modalHint}>NSE symbol recommended, e.g. TCS.NS or RELIANCE.NS</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="Symbol or company name"
                placeholderTextColor={colors.textMuted}
                value={form.symbol}
                onChangeText={(v) => setForm((f) => ({ ...f, symbol: v }))}
                onFocus={() => setSymbolFocused(true)}
                onBlur={() => setTimeout(() => setSymbolFocused(false), 200)}
                autoCapitalize="characters"
                autoCorrect={false}
                returnKeyType="next"
              />
              <SymbolSuggestionDrawer
                query={form.symbol}
                visible={symbolFocused}
                onSelect={(sym) => {
                  setForm((f) => ({ ...f, symbol: sym }));
                  setSymbolFocused(false);
                  Keyboard.dismiss();
                }}
              />
              <TextInput
                style={styles.modalInput}
                placeholder="Quantity"
                placeholderTextColor={colors.textMuted}
                value={form.quantity}
                onChangeText={(v) => setForm((f) => ({ ...f, quantity: v }))}
                keyboardType={Platform.OS === 'ios' ? 'decimal-pad' : 'numeric'}
              />
              <TextInput
                style={styles.modalInput}
                placeholder="Avg buy price (₹)"
                placeholderTextColor={colors.textMuted}
                value={form.avg_buy_price}
                onChangeText={(v) => setForm((f) => ({ ...f, avg_buy_price: v }))}
                keyboardType={Platform.OS === 'ios' ? 'decimal-pad' : 'numeric'}
              />
              <View style={styles.modalActions}>
                <TouchableOpacity
                  onPress={() => { setSymbolFocused(false); setShowAdd(false); }}
                  style={styles.cancelBtn}
                >
                  <Text style={styles.cancelBtnText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => {
                    if (!form.symbol.trim() || !form.quantity || !form.avg_buy_price) {
                      Alert.alert('Missing fields', 'Enter symbol, quantity, and average buy price.');
                      return;
                    }
                    addMutation.mutate();
                  }}
                  style={[styles.confirmBtn, addMutation.isPending && styles.confirmBtnDisabled]}
                  disabled={addMutation.isPending}
                >
                  <Text style={styles.confirmBtnText}>
                    {addMutation.isPending ? 'Adding…' : 'Add'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  summaryCard: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginTop: spacing.sm,
    marginBottom: spacing.md,
    gap: spacing.sm,
  },
  summaryTitle: {
    fontSize: font.xs,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  summaryRow: { flexDirection: 'row', gap: spacing.md },
  summaryCell: { flex: 1 },
  summaryLabel: { fontSize: font.xs, color: colors.textMuted, fontWeight: '600' },
  summaryValue: { fontSize: font.xl, fontWeight: '800', color: colors.textPrimary, marginTop: 4 },
  summaryPnl: { fontSize: font.lg, fontWeight: '700' },
  addBtn: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  addBtnText: { color: '#fff', fontWeight: '700', fontSize: font.md },
  errorText: { color: colors.red, fontSize: font.sm, marginBottom: spacing.sm },
  holdingCard: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
  },
  holdingTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  holdingMain: { flex: 1, paddingRight: spacing.sm },
  holdingSymbol: { fontSize: font.lg, fontWeight: '800', color: colors.textPrimary },
  removeBtn: {
    backgroundColor: colors.redDim,
    borderRadius: radius.sm,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  removeBtnText: { color: colors.red, fontSize: font.xs, fontWeight: '700' },
  holdingMeta: { fontSize: font.sm, color: colors.textSecondary, marginTop: 4 },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.sm,
    gap: spacing.sm,
  },
  statCell: { width: '47%' },
  statLabel: { fontSize: font.xs, color: colors.textMuted, fontWeight: '600' },
  statValue: { fontSize: font.sm, fontWeight: '700', color: colors.textPrimary, marginTop: 2 },
  separator: { height: spacing.sm },
  loader: { position: 'absolute', top: '40%', alignSelf: 'center' },
  modalOverlay: { flex: 1, justifyContent: 'flex-end' },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.65)',
  },
  modalScrollContent: { flexGrow: 1, justifyContent: 'flex-end' },
  modal: {
    backgroundColor: colors.card,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    padding: spacing.lg,
    gap: spacing.sm,
    borderWidth: 1,
    borderBottomWidth: 0,
    borderColor: colors.border,
  },
  modalTitle: { fontSize: font.xl, fontWeight: '700', color: colors.textPrimary },
  modalHint: { fontSize: font.xs, color: colors.textMuted, marginBottom: spacing.xs },
  modalInput: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: 14,
    color: colors.textPrimary,
    fontSize: font.md,
  },
  modalActions: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm },
  cancelBtn: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
  },
  cancelBtnText: { color: colors.textSecondary, fontWeight: '600' },
  confirmBtn: { flex: 1, backgroundColor: colors.accent, borderRadius: radius.md, paddingVertical: 14, alignItems: 'center' },
  confirmBtnDisabled: { opacity: 0.5 },
  confirmBtnText: { color: '#fff', fontWeight: '700' },
});
