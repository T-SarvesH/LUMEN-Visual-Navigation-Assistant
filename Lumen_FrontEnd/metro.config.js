const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');
const path = require('path');

const defaultConfig = getDefaultConfig(__dirname);

const config = {
  resolver: {
    extraNodeModules: {
      // Force Metro to resolve event-target-shim correctly
      'event-target-shim': path.resolve(
        __dirname,
        'node_modules/event-target-shim'
      ),
    },
  },
};

module.exports = mergeConfig(defaultConfig, config);
