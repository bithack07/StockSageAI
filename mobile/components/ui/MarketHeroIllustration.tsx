import Svg, {
  Circle, Defs, G, LinearGradient, Rect, Stop, Text as SvgText,
} from 'react-native-svg';
import { colors } from '@/constants/theme';

const W = 320;
const H = 200;

interface Props {
  width?: number;
  height?: number;
}

export function MarketHeroIllustration({ width = W, height = H }: Props) {
  return (
    <Svg width={width} height={height} viewBox={`0 0 ${W} ${H}`}>
      <Defs>
        <LinearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor={colors.accent} stopOpacity="0.25" />
          <Stop offset="1" stopColor="#6366F1" stopOpacity="0.06" />
        </LinearGradient>
      </Defs>
      <Rect x={8} y={8} width={304} height={184} rx={16} fill="url(#bg)" stroke={colors.border} />
      <Circle cx={28} cy={28} r={5} fill={colors.red} opacity={0.8} />
      <Circle cx={44} cy={28} r={5} fill={colors.yellow} opacity={0.8} />
      <Circle cx={60} cy={28} r={5} fill={colors.green} opacity={0.8} />
      <SvgText x={76} y={32} fill={colors.textSecondary} fontSize={11} fontWeight="600">
        Live Analysis
      </SvgText>

      {[0, 1, 2, 3].map((i) => (
        <Rect key={i} x={20} y={50 + i * 32} width={280} height={1} fill={colors.border} opacity={0.6} />
      ))}

      <G>
        <Rect x={40} y={120} width={10} height={36} rx={2} fill={colors.green} />
        <Rect x={58} y={130} width={10} height={26} rx={2} fill={colors.red} />
        <Rect x={76} y={110} width={10} height={46} rx={2} fill={colors.green} />
        <Rect x={94} y={100} width={10} height={56} rx={2} fill={colors.green} />
        <Rect x={112} y={115} width={10} height={41} rx={2} fill={colors.red} />
        <Rect x={130} y={90} width={10} height={66} rx={2} fill={colors.green} />
        <Rect x={148} y={105} width={10} height={51} rx={2} fill={colors.green} />
        <Rect x={166} y={85} width={10} height={71} rx={2} fill={colors.green} />
        <Rect x={184} y={95} width={10} height={61} rx={2} fill={colors.red} />
        <Rect x={202} y={75} width={10} height={81} rx={2} fill={colors.green} />
        <Rect x={220} y={88} width={10} height={68} rx={2} fill={colors.green} />
        <Rect x={238} y={70} width={10} height={86} rx={2} fill={colors.green} />
      </G>

      <Rect x={200} y={48} width={96} height={32} rx={8} fill={colors.card} stroke={colors.green} strokeWidth={1} />
      <SvgText x={212} y={64} fill={colors.green} fontSize={10} fontWeight="800">
        BULLISH
      </SvgText>
      <SvgText x={212} y={76} fill={colors.textSecondary} fontSize={8}>
        AI 78%
      </SvgText>
    </Svg>
  );
}
