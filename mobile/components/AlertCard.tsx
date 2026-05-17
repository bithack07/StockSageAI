import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

interface Alert {
  id: string;
  symbol: string;
  condition: string;
  threshold: number | null;
  is_active: boolean;
  created_at: string;
}

interface Props {
  alert: Alert;
  onDelete: (id: string) => void;
}

export function AlertCard({ alert, onDelete }: Props) {
  return (
    <View style={[styles.card, !alert.is_active && styles.inactive]}>
      <View style={styles.info}>
        <Text style={styles.symbol}>{alert.symbol}</Text>
        <Text style={styles.condition}>
          {alert.condition.replace(/_/g, ' ')}
          {alert.threshold != null ? ` ${alert.threshold}` : ''}
        </Text>
        <Text style={styles.status}>{alert.is_active ? '🟢 Active' : '⚫ Triggered'}</Text>
      </View>
      {alert.is_active && (
        <TouchableOpacity onPress={() => onDelete(alert.id)} style={styles.deleteBtn}>
          <Text style={styles.deleteBtnText}>Delete</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  inactive: { opacity: 0.5 },
  info: { flex: 1, gap: 3 },
  symbol: { fontSize: 16, fontWeight: '700', color: '#f8fafc' },
  condition: { fontSize: 13, color: '#94a3b8', textTransform: 'capitalize' },
  status: { fontSize: 12, color: '#64748b', marginTop: 2 },
  deleteBtn: { backgroundColor: '#450a0a', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6 },
  deleteBtnText: { color: '#fca5a5', fontWeight: '600', fontSize: 13 },
});
