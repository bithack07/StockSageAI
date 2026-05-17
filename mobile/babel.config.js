module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    // Reanimated 4: worklets plugin must be last (replaces reanimated/plugin)
    plugins: ['react-native-worklets/plugin'],
  };
};
