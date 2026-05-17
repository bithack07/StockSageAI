import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Dimensions,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  type ViewStyle,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { investor } from '@/api/client';
import { GuideLink } from '@/components/ui/GuideLink';
import { colors, font, radius, spacing } from '@/constants/theme';

const CHECKLIST_ITEMS = [
  { key: 'understand_business', label: 'I understand how this business makes money' },
  { key: 'circle_of_competence', label: 'Within my circle of competence' },
  { key: 'comfortable_10y', label: 'Comfortable holding 10+ years' },
] as const;

type ChecklistKey = (typeof CHECKLIST_ITEMS)[number]['key'];

type OwnerChecklist = {
  moat_rating?: number | null;
  management_rating?: number | null;
  circle_of_competence?: boolean | null;
  understand_business?: boolean | null;
  comfortable_10y?: boolean | null;
  notes?: string | null;
};

interface Props {
  symbol: string;
  visible: boolean;
  onClose: () => void;
}

/** Bottom-sheet height caps — Android ignores parent maxHeight unless scroll area is numeric. */
function sheetLayout(windowHeight: number) {
  const sheetMaxHeight = Math.round(
    windowHeight * (Platform.OS === 'android' ? 0.58 : 0.72),
  );
  const scrollMaxHeight = Math.max(200, sheetMaxHeight - 152);
  return { sheetMaxHeight, scrollMaxHeight };
}

export function OwnerChecklistDrawer({ symbol, visible, onClose }: Props) {
  const insets = useSafeAreaInsets();
  const qc = useQueryClient();
  const [draft, setDraft] = useState<Partial<OwnerChecklist>>({});
  const [moatText, setMoatText] = useState('');
  const [mgmtText, setMgmtText] = useState('');
  const [notesText, setNotesText] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['buffett-kit', symbol],
    queryFn: () => investor.buffettKit(symbol).then((r) => r.data),
    enabled: visible && !!symbol,
  });

  const cl: OwnerChecklist = data?.owner_checklist ?? {};

  useEffect(() => {
    if (!visible) return;
    setDraft({});
    setMoatText(cl.moat_rating != null ? String(cl.moat_rating) : '');
    setMgmtText(cl.management_rating != null ? String(cl.management_rating) : '');
    setNotesText(cl.notes ?? '');
  }, [visible, symbol, data?.owner_checklist]);

  const saveCl = useMutation({
    mutationFn: (body: object) => investor.saveChecklist(symbol, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['buffett-kit', symbol] });
      setDraft({});
    },
  });

  const isChecked = (key: ChecklistKey): boolean => {
    if (key in draft) return Boolean(draft[key]);
    return Boolean(cl[key]);
  };

  const toggleItem = (key: ChecklistKey) => {
    const next = !isChecked(key);
    setDraft((prev) => ({ ...prev, [key]: next }));
    saveCl.mutate({ [key]: next });
  };

  const saveFullChecklist = () => {
    const moat = moatText.trim() ? parseInt(moatText, 10) : null;
    const mgmt = mgmtText.trim() ? parseInt(mgmtText, 10) : null;
    saveCl.mutate({
      understand_business: isChecked('understand_business'),
      circle_of_competence: isChecked('circle_of_competence'),
      comfortable_10y: isChecked('comfortable_10y'),
      moat_rating: moat && moat >= 1 && moat <= 5 ? moat : null,
      management_rating: mgmt && mgmt >= 1 && mgmt <= 5 ? mgmt : null,
      notes: notesText.trim() || null,
    });
  };

  const { sheetMaxHeight, scrollMaxHeight } = sheetLayout(Dimensions.get('window').height);
  const sheetStyle: ViewStyle[] = [
    styles.sheet,
    {
      maxHeight: sheetMaxHeight,
      paddingBottom: Math.max(insets.bottom, spacing.md),
    },
  ];

  const sheetBody = (
    <>
      <View style={styles.sheetHeader}>
        <View style={styles.handle} />
        <Text style={styles.title}>Owner checklist</Text>
        <Text style={styles.sub}>Personal due diligence for {symbol.replace(/\.(NS|BO)$/i, '')}</Text>
        <GuideLink section="owner-investing" label="What is the owner checklist?" />
      </View>

      <ScrollView
        style={[styles.sheetScroll, { maxHeight: scrollMaxHeight }]}
        contentContainerStyle={styles.sheetScrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={Platform.OS === 'android'}
        nestedScrollEnabled
        bounces={false}
      >
        {isLoading ? (
          <ActivityIndicator color={colors.accent} style={{ marginVertical: spacing.lg }} />
        ) : (
          <>
            {CHECKLIST_ITEMS.map(({ key, label }) => {
              const checked = isChecked(key);
              return (
                <Pressable
                  key={key}
                  style={[styles.checkRow, checked && styles.checkRowChecked]}
                  onPress={() => toggleItem(key)}
                  disabled={saveCl.isPending}
                >
                  <Ionicons
                    name={checked ? 'checkbox' : 'square-outline'}
                    size={22}
                    color={checked ? colors.accent : colors.textMuted}
                  />
                  <Text style={[styles.checkLabel, checked && styles.checkLabelChecked]}>{label}</Text>
                </Pressable>
              );
            })}
            <View style={styles.ratingRow}>
              <Text style={styles.ratingLabel}>Moat (1–5)</Text>
              <TextInput
                style={styles.ratingInput}
                value={moatText}
                onChangeText={setMoatText}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor={colors.textMuted}
                maxLength={1}
              />
            </View>
            <View style={styles.ratingRow}>
              <Text style={styles.ratingLabel}>Management (1–5)</Text>
              <TextInput
                style={styles.ratingInput}
                value={mgmtText}
                onChangeText={setMgmtText}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor={colors.textMuted}
                maxLength={1}
              />
            </View>
            <TextInput
              style={styles.notesInput}
              value={notesText}
              onChangeText={setNotesText}
              placeholder="Notes (moat, governance, regulatory risks…)"
              placeholderTextColor={colors.textMuted}
              multiline
            />
            <TouchableOpacity
              style={[styles.saveBtn, saveCl.isPending && styles.saveBtnDisabled]}
              onPress={saveFullChecklist}
              disabled={saveCl.isPending}
            >
              <Text style={styles.saveBtnText}>{saveCl.isPending ? 'Saving…' : 'Save checklist'}</Text>
            </TouchableOpacity>
          </>
        )}
      </ScrollView>

      <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
        <Text style={styles.closeBtnText}>Close</Text>
      </TouchableOpacity>
    </>
  );

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.modalRoot}>
        <Pressable style={styles.backdrop} onPress={onClose} />
        {Platform.OS === 'ios' ? (
          <KeyboardAvoidingView behavior="padding" style={sheetStyle}>
            {sheetBody}
          </KeyboardAvoidingView>
        ) : (
          <View style={sheetStyle}>{sheetBody}</View>
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalRoot: { flex: 1, justifyContent: 'flex-end' },
  backdrop: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.6)' },
  sheet: {
    width: '100%',
    alignSelf: 'stretch',
    backgroundColor: colors.card,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    borderWidth: 1,
    borderBottomWidth: 0,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  sheetHeader: { flexShrink: 0 },
  sheetScroll: { flexGrow: 0 },
  sheetScrollContent: { flexGrow: 0, paddingBottom: spacing.xs },
  handle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.border,
    alignSelf: 'center',
    marginBottom: spacing.md,
  },
  title: { fontSize: font.xl, fontWeight: '800', color: colors.textPrimary },
  sub: { fontSize: font.sm, color: colors.textMuted, marginTop: 4, marginBottom: spacing.sm },
  checkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderRadius: radius.md,
    marginTop: 4,
  },
  checkRowChecked: { backgroundColor: colors.accentDim },
  checkLabel: { flex: 1, fontSize: font.sm, color: colors.textSecondary, marginLeft: 10 },
  checkLabelChecked: { color: colors.textPrimary, fontWeight: '600' },
  ratingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 },
  ratingLabel: { fontSize: font.xs, color: colors.textMuted },
  ratingInput: {
    width: 48,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.sm,
    color: colors.textPrimary,
    textAlign: 'center',
    fontSize: font.sm,
  },
  notesInput: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.sm,
    color: colors.textPrimary,
    marginTop: 8,
    minHeight: 64,
    maxHeight: 96,
    fontSize: font.sm,
    textAlignVertical: 'top',
  },
  saveBtn: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 10,
    minHeight: 44,
  },
  saveBtnDisabled: { opacity: 0.6 },
  saveBtnText: { color: '#fff', fontWeight: '700', fontSize: font.md },
  closeBtn: {
    flexShrink: 0,
    paddingVertical: 10,
    alignItems: 'center',
  },
  closeBtnText: { color: colors.textSecondary, fontWeight: '600', fontSize: font.sm },
});
