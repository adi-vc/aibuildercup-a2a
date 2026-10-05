/**
 * DepthParallax.tsx — L1 motion from a depth map (vachan-plan.md §47, F11).
 *
 * A WebGL fragment shader displaces each pixel's lookup by its depth, so near
 * things (white in the map) slide against far things (black) as a virtual
 * camera drifts. The drift is a pure function of the frame, so the same frame
 * always renders the same pixels (Remotion's determinism rule, and what makes
 * an offline export match the live player).
 *
 * Any failure — no WebGL, a texture that won't load — calls onFallback and
 * the hold drops a rung to Ken Burns; it never blocks the text layer.
 */

import { useEffect, useRef, useState } from 'react';
import { continueRender, delayRender, useCurrentFrame } from 'remotion';
import { HEIGHT, parallaxOffset, WIDTH } from './timeline';

const VERTEX = `
attribute vec2 a_pos;
varying vec2 v_uv;
void main() {
  v_uv = a_pos * 0.5 + 0.5;
  gl_Position = vec4(a_pos, 0.0, 1.0);
}`;

const FRAGMENT = `
precision mediump float;
uniform sampler2D u_plate;
uniform sampler2D u_depth;
uniform vec2 u_offset;
varying vec2 v_uv;
void main() {
  // Overscan 4% so displaced lookups never sample past the plate's edge.
  vec2 uv = 0.5 + (v_uv - 0.5) * 0.96;
  float depth = texture2D(u_depth, uv).r;          // 1 = near, 0 = far
  uv += u_offset * (depth - 0.4);                  // near moves against far
  gl_FragColor = texture2D(u_plate, clamp(uv, 0.0, 1.0));
}`;

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous'; // CDN plates must be CORS-readable to become textures
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`could not load ${src}`));
    img.src = src;
  });
}

function compile(gl: WebGLRenderingContext, type: number, source: string): WebGLShader {
  const shader = gl.createShader(type)!;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader) ?? 'shader');
  return shader;
}

function texture(gl: WebGLRenderingContext, unit: number, img: HTMLImageElement): void {
  gl.activeTexture(gl.TEXTURE0 + unit);
  gl.bindTexture(gl.TEXTURE_2D, gl.createTexture());
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
}

interface Props {
  plateSrc: string;
  depthSrc: string;
  className?: string;
  onReady?: () => void;
  onFallback: () => void;
}

export function DepthParallax({ plateSrc, depthSrc, className, onReady, onFallback }: Props) {
  const frame = useCurrentFrame();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const glRef = useRef<{ gl: WebGLRenderingContext; offset: WebGLUniformLocation } | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const handle = delayRender(`parallax textures ${plateSrc}`);
    let cancelled = false;
    (async () => {
      try {
        const gl = canvasRef.current?.getContext('webgl', { premultipliedAlpha: false, preserveDrawingBuffer: true });
        if (!gl) throw new Error('webgl unavailable');
        const [plate, depth] = await Promise.all([loadImage(plateSrc), loadImage(depthSrc)]);
        if (cancelled) return;
        const program = gl.createProgram()!;
        gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERTEX));
        gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAGMENT));
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error('link failed');
        gl.useProgram(program);
        gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
        const pos = gl.getAttribLocation(program, 'a_pos');
        gl.enableVertexAttribArray(pos);
        gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);
        texture(gl, 0, plate);
        texture(gl, 1, depth);
        gl.uniform1i(gl.getUniformLocation(program, 'u_plate'), 0);
        gl.uniform1i(gl.getUniformLocation(program, 'u_depth'), 1);
        glRef.current = { gl, offset: gl.getUniformLocation(program, 'u_offset')! };
        setReady(true);
      } catch {
        if (!cancelled) onFallback();
      } finally {
        continueRender(handle);
      }
    })();
    return () => {
      cancelled = true;
      continueRender(handle);
    };
    // onFallback is a stable setter from the parent; textures reload only on new sources.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plateSrc, depthSrc]);

  useEffect(() => {
    const ctx = glRef.current;
    if (!ready || !ctx) return;
    const [x, y] = parallaxOffset(frame);
    ctx.gl.viewport(0, 0, WIDTH, HEIGHT);
    ctx.gl.uniform2f(ctx.offset, x, y);
    ctx.gl.drawArrays(ctx.gl.TRIANGLE_STRIP, 0, 4);
    onReady?.();
  }, [frame, ready, onReady]);

  return <canvas ref={canvasRef} width={WIDTH} height={HEIGHT} className={className} />;
}
