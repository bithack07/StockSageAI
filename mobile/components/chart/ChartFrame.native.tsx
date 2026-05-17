import { Platform, StyleSheet, View } from 'react-native';
import { WebView } from 'react-native-webview';

type Props = {
  html: string;
  height: number;
};

/**
 * Fixed-height WebView — must NOT use flex:1 inside a ScrollView or it steals
 * touches across the whole screen on iOS/Android.
 */
export function ChartFrame({ html, height }: Props) {
  return (
    <View
      style={[styles.shell, { height }]}
      collapsable={false}
      pointerEvents="box-none"
    >
      <WebView
        source={{ html, baseUrl: 'https://stocksage.local' }}
        style={{ height, width: '100%', backgroundColor: '#0f172a' }}
        scrollEnabled={false}
        javaScriptEnabled
        domStorageEnabled
        originWhitelist={['*']}
        allowsInlineMediaPlayback
        setSupportMultipleWindows={false}
        androidLayerType={Platform.OS === 'android' ? 'hardware' : undefined}
        nestedScrollEnabled={false}
        overScrollMode="never"
        bounces={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  shell: {
    width: '100%',
    overflow: 'hidden',
    backgroundColor: '#0f172a',
  },
});
