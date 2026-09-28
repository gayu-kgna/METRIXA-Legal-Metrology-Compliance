import '@testing-library/jest-dom';

// Ensure ImageData polyfill exists in jsdom environment if missing
if (typeof globalThis.ImageData === 'undefined') {
  class ImageDataPolyfill {
    width: number;
    height: number;
    data: Uint8ClampedArray;
    colorSpace: PredefinedColorSpace = 'srgb';

    constructor(dataOrWidth: Uint8ClampedArray | number, widthOrHeight: number, maybeHeight?: number) {
      if (typeof dataOrWidth === 'number') {
        this.width = dataOrWidth;
        this.height = widthOrHeight;
        this.data = new Uint8ClampedArray(this.width * this.height * 4);
      } else {
        this.data = dataOrWidth;
        this.width = widthOrHeight;
        this.height = maybeHeight || (dataOrWidth.length / (widthOrHeight * 4));
      }
    }
  }
  (globalThis as any).ImageData = ImageDataPolyfill;
}

// Ensure mock canvas getContext returns realistic 2D methods
if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = function (contextType: string) {
    if (contextType === '2d') {
      return {
        drawImage: () => {},
        getImageData: (sx: number, sy: number, sw: number, sh: number) => {
          return new ImageData(sw, sh);
        },
        putImageData: () => {},
        fillRect: () => {},
        clearRect: () => {},
      } as any;
    }
    return null;
  } as any;

  HTMLCanvasElement.prototype.toBlob = function (callback: (blob: Blob | null) => void, type?: string) {
    callback(new Blob(['fake_jpeg_bytes'], { type: type || 'image/jpeg' }));
  };
}
