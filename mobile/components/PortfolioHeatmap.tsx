import { StyleSheet, Text, View } from 'react-native';

interface Holding {
  symbol: string;
  current_value: number;
  pnl_pct: number;
}

interface Props {
  holdings: Holding[];
}

function interpolateColor(pct: number): string {
  if (pct > 5) return '#14532d';
  if (pct > 0) return '#166534';
  if (pct === 0) return '#1e293b';
  if (pct > -5) return '#7f1d1d';
  return '#450a0a';
}

export function PortfolioHeatmap({ holdings }: Props) {
  const total = holdings.reduce((sum, h) => sum + h.current_value, 0);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Sector Heatmap</Text>
      <View style={styles.grid}>
        {holdings.map((h) => {
          const weight = total > 0 ? (h.current_value / total) * 100 : 0;
          const bgColor = interpolateColor(h.pnl_pct);
          return (
            <View
              key={h.symbol}
              style={[
                styles.cell,
                { backgroundColor: bgColor, flex: Math.max(weight / 10, 1) },
              ]}
            >
              <Text style={styles.cellSymbol}>{h.symbol.replace('.NS', '')}</Text>
              <Text style={[styles.cellPnl, { color: h.pnl_pct >= 0 ? '#86efac' : '#fca5a5' }]}>
                {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct.toFixed(1)}%
              </Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16 },
  title: { fontSize: 14, fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 4 },
  cell: { borderRadius: 8, padding: 10, minWidth: 64, alignItems: 'center', justifyContent: 'center' },
  cellSymbol: { fontSize: 11, fontWeight: '700', color: '#f8fafc' },
  cellPnl: { fontSize: 10, marginTop: 2 },
});
