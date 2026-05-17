import { useEffect, useRef } from 'react';
import { Animated, Dimensions, StyleSheet, View } from 'react-native';
import Svg, { Defs, LinearGradient, Path, Stop } from 'react-native-svg';
import { colors } from '@/constants/theme';

const { width, height } = Dimensions.get('window');

export function AnimatedBackground() {
  const orb1 = useRef(new Animated.Value(0)).current;
  const orb2 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = (val: Animated.Value, duration: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(val, { toValue: 1, duration, useNativeDriver: true }),
          Animated.timing(val, { toValue: 0, duration, useNativeDriver: true }),
        ]),
      ).start();

    loop(orb1, 9000);
    loop(orb2, 12000);
  }, [orb1, orb2]);

  const t1 = orb1.interpolate({ inputRange: [0, 1], outputRange: [0, 24] });
  const t2 = orb2.interpolate({ inputRange: [0, 1], outputRange: [0, -20] });

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Animated.View
        style={[
          styles.orb,
          styles.orbBlue,
          { transform: [{ translateY: t1 }, { translateX: t2 }] },
        ]}
      />
      <Animated.View
        style={[
          styles.orb,
          styles.orbPurple,
          { right: -40, bottom: height * 0.15, transform: [{ translateY: t2 }] },
        ]}
      />
      <Svg width={width} height={height * 0.35} style={styles.chart}>
        <Defs>
          <LinearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
            <Stop offset="0" stopColor={colors.accent} stopOpacity="0.5" />
            <Stop offset="1" stopColor={colors.green} stopOpacity="0.2" />
          </LinearGradient>
        </Defs>
        <Path
          d={`M0 ${height * 0.2} Q ${width * 0.25} ${height * 0.08} ${width * 0.5} ${height * 0.14} T ${width} ${height * 0.06}`}
          stroke="url(#lineGrad)"
          strokeWidth={2}
          fill="none"
        />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  orb: {
    position: 'absolute',
    width: 280,
    height: 280,
    borderRadius: 140,
    opacity: 0.35,
  },
  orbBlue: {
    top: -60,
    left: -80,
    backgroundColor: colors.accent,
  },
  orbPurple: {
    backgroundColor: '#6366F1',
  },
  chart: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    opacity: 0.4,
  },
});
