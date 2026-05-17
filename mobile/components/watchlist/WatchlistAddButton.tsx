import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity } from 'react-native';
import { watchlist } from '@/api/client';
import { isOnWatchlist } from '@/lib/watchlistMatch';
import { colors, font, radius } from '@/constants/theme';

type WatchlistRow = { id: string; symbol?: string; canonical_symbol?: string };

type Props = {
  symbol: string;
  watchlistItems: WatchlistRow[];
};

export function WatchlistAddButton({ symbol, watchlistItems }: Props) {
  const qc = useQueryClient();
  const onList = isOnWatchlist(symbol, watchlistItems);

  const addMutation = useMutation({
    mutationFn: () => watchlist.add(symbol),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  if (onList) {
    return (
      <TouchableOpacity style={[styles.btn, styles.btnOnList]} disabled activeOpacity={1}>
        <Ionicons name="bookmark" size={16} color={colors.accent} />
        <Text style={[styles.btnText, styles.btnTextOnList]}>On watchlist</Text>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      style={styles.btn}
      onPress={() => addMutation.mutate()}
      disabled={addMutation.isPending}
      activeOpacity={0.7}
    >
      {addMutation.isPending ? (
        <ActivityIndicator size="small" color={colors.accent} />
      ) : (
        <>
          <Ionicons name="bookmark-outline" size={16} color={colors.accent} />
          <Text style={styles.btnText}>Add</Text>
        </>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.accent,
    backgroundColor: colors.accentDim,
    minWidth: 72,
    justifyContent: 'center',
  },
  btnOnList: { opacity: 0.85 },
  btnText: { fontSize: font.xs, fontWeight: '700', color: colors.accent },
  btnTextOnList: { color: colors.textSecondary },
});
