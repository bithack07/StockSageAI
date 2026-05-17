import { StyleSheet, View } from 'react-native';

type Props = {
  html: string;
  height: number;
  baseUrl?: string;
};

/** Web / Expo web — iframe (react-native-webview does not support web) */
export function ChartFrame({ html, height }: Props) {
  return (
    <View style={[styles.wrap, { height }]}>
      <iframe
        srcDoc={html}
        title="Stock chart"
        style={{
          width: '100%',
          height: '100%',
          border: 'none',
          backgroundColor: '#0f172a',
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: '100%', overflow: 'hidden', backgroundColor: '#0f172a' },
});
