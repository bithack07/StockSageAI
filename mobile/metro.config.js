const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);
// Chart lib as asset — do NOT add "js" here (breaks Metro + expo-router web SSR)
config.resolver.assetExts.push('bundle');

module.exports = config;
