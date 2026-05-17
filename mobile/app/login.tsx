import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { router } from 'expo-router';
import { auth } from '@/api/client';
import { getApiConfigLabel, pingBackend } from '@/lib/apiConfig';
import { AnimatedBackground } from '@/components/ui/AnimatedBackground';
import { MarketHeroIllustration } from '@/components/ui/MarketHeroIllustration';
import { useUserStore } from '@/store/userStore';
import { colors, font, radius, spacing } from '@/constants/theme';

export default function LoginScreen() {
  const login = useUserStore((s) => s.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [backendStatus, setBackendStatus] = useState<'checking' | 'ok' | 'fail'>('checking');
  const [backendMessage, setBackendMessage] = useState('');

  useEffect(() => {
    let cancelled = false;
    pingBackend().then((r) => {
      if (cancelled) return;
      setBackendStatus(r.ok ? 'ok' : 'fail');
      setBackendMessage(r.ok ? `API: ${getApiConfigLabel()}` : r.message);
    });
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async () => {
    if (!email || !password) { setError('Enter email and password'); return; }
    setLoading(true);
    setError('');
    try {
      const fn = isRegister ? auth.register : auth.login;
      const { data } = await fn(email.trim().toLowerCase(), password);
      await login(data.user_id, email.trim().toLowerCase(), data.access_token, data.refresh_token);
      router.replace('/(tabs)');
    } catch (e: any) {
      if (!e?.response) {
        setError(
          `Network error — cannot reach ${getApiConfigLabel()}. ` +
          'Start backend: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000. Phone and Mac must be on the same Wi‑Fi.',
        );
      } else {
        const msg = e?.response?.data?.detail ?? (isRegister ? 'Registration failed' : 'Invalid credentials');
        setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <AnimatedBackground />

      <MarketHeroIllustration />

      <View style={styles.logoRow}>
        <View style={styles.logoMark}>
          <Text style={styles.logoIcon}>◈</Text>
        </View>
        <Text style={styles.logoText}>StockSage AI</Text>
      </View>
      <Text style={styles.tagline}>Agentic intelligence for Indian equities</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{isRegister ? 'Create account' : 'Welcome back'}</Text>

        <View style={styles.field}>
          <Text style={styles.label}>Email</Text>
          <TextInput
            style={styles.input}
            placeholder="you@example.com"
            placeholderTextColor={colors.textMuted}
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            placeholder="••••••••"
            placeholderTextColor={colors.textMuted}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />
        </View>

        {error !== '' && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        <TouchableOpacity
          style={[styles.btn, loading && styles.btnDisabled]}
          onPress={handleSubmit}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.btnText}>{isRegister ? 'Create Account' : 'Sign In'}</Text>
          }
        </TouchableOpacity>

        <TouchableOpacity onPress={() => { setIsRegister((v) => !v); setError(''); }}>
          <Text style={styles.toggleText}>
            {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
          </Text>
        </TouchableOpacity>
      </View>

      <View style={[
        styles.backendBanner,
        backendStatus === 'ok' ? styles.backendOk : backendStatus === 'fail' ? styles.backendFail : null,
      ]}>
        <Text style={styles.backendBannerText}>
          {backendStatus === 'checking' ? 'Checking backend…' : backendMessage}
        </Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  logoRow: {
    marginTop: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  logoMark: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    backgroundColor: colors.accentDim,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.accent,
  },
  logoIcon: { fontSize: 20, color: colors.accent },
  logoText: { fontSize: font.xxl, fontWeight: '800', color: colors.textPrimary, letterSpacing: -0.5 },
  tagline: { fontSize: font.sm, color: colors.textMuted, marginBottom: spacing.xl },
  card: {
    width: '100%',
    backgroundColor: colors.card,
    borderRadius: radius.xl,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.md,
  },
  cardTitle: { fontSize: font.xl, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.xs },
  field: { gap: spacing.xs },
  label: { fontSize: font.xs, fontWeight: '700', color: colors.textSecondary, textTransform: 'uppercase', letterSpacing: 0.5 },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    color: colors.textPrimary,
    fontSize: font.md,
  },
  errorBox: {
    backgroundColor: colors.redDim,
    borderRadius: radius.sm,
    padding: spacing.sm,
    borderWidth: 1,
    borderColor: colors.red,
  },
  errorText: { color: colors.red, fontSize: font.sm },
  btn: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: spacing.xs,
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#fff', fontWeight: '700', fontSize: font.md },
  toggleText: { color: colors.textSecondary, fontSize: font.sm, textAlign: 'center' },
  backendBanner: {
    marginTop: spacing.lg,
    width: '100%',
    padding: spacing.sm,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  backendOk: { borderColor: colors.green, backgroundColor: colors.greenDim },
  backendFail: { borderColor: colors.red, backgroundColor: colors.redDim },
  backendBannerText: { fontSize: font.xs, color: colors.textSecondary, textAlign: 'center', lineHeight: 18 },
});
