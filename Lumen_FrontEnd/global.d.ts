// src/global.d.ts
declare global {
  var __frameProcessorPlugins: {
    [key: string]: (frame: any) => any;
  };
}

export {};
