Includes = { "buttonstate.fxh" }

PixelShader = {
    Samplers = {
        MapTexture = {
            Index = 0
            MagFilter = "Linear"
            MinFilter = "Linear"
            MipFilter = "None"
            AddressU = "Clamp"
            AddressV = "Clamp"
        }
    }
}

VertexStruct VS_OUTPUT
{
    float4 vPosition : PDX_POSITION;
    float3 framePixel : TEXCOORD0;
};

VertexShader = {
    MainCode VertexShader
    [[
        VS_OUTPUT main(const VS_INPUT v)
        {
            VS_OUTPUT Out;
            Out.vPosition = mul(WorldViewProjectionMatrix, float4(v.vPosition, 1.0));
            float frameCount = 120.0;
            float2 uv = saturate(v.vTexCoord * float2(frameCount, 1.0));
            float frame = clamp(floor(Offset.x * frameCount + 0.5), 0.0, frameCount - 1.0);
            Out.framePixel = float3(uv * float2(1920.0, 1440.0), frame + 0.5);

            // Fill the viewport with the same centred 4:3 crop as the menu background.
            float clipWidth = mul(WorldViewProjectionMatrix, float4(1, 0, 0, 0)).x;
            float clipHeight = mul(WorldViewProjectionMatrix, float4(0, 1, 0, 0)).y;
            float aspect = abs(clipHeight / clipWidth);
            float2 cover = max(float2(1, 1), float2(4.0 / (3.0 * aspect), aspect * 0.75));
            Out.vPosition.xy = (float2(uv.x, 1.0 - uv.y) * 2.0 - 1.0) * cover * Out.vPosition.w;
            return Out;
        }
    ]]
}

PixelShader = {
    MainCode PixelShader
    [[
        float4 main(VS_OUTPUT v) : PDX_COLOR
        {
            // Every sky cell owns one star. Keep its entire halo inside the cell.
            float2 cell = floor(v.framePixel.xy / 148.0);
            float2 seed = frac(cell * float2(0.1031, 0.11369));
            float3 h = frac(float3(seed.x, seed.y, seed.x) + float3(0.17, 0.41, 0.73));
            h += dot(h, h.yzx + 33.33);
            float3 noise = frac((h.xxy + h.yzz) * h.zyx);
            float2 center = 12.0 + 124.0 * noise.xy;
            float2 p = abs(v.framePixel.xy - cell * 148.0 - center);

            // Eight-second cycle: unfold, shimmer for two seconds, then fade.
            float age = frac((v.framePixel.z - 0.5) / 120.0 + noise.z) * 8.0;
            float open = smoothstep(0.0, 0.8, age);
            float fade = 1.0 - smoothstep(2.8, 4.0, age);
            float radius = lerp(0.8, 4.5 + 2.5 * noise.x, open);
            float contour = sqrt(p.x) + sqrt(p.y);
            float rays = saturate((radius - contour * contour) * 0.85 + 0.5);
            float halo = 0.18 * exp2(-dot(p,p) / 5.0);
            float shimmer = 0.94 + 0.06 * sin(6.283185 * (age + noise.y));
            float alpha = saturate(rays + halo) * open * fade * shimmer * Color.a;
            return float4(Color.rgb * alpha, alpha);
        }
    ]]
}

BlendState BlendState
{
    BlendEnable = yes
    SourceBlend = "one"
    DestBlend = "inv_src_alpha"
}

Effect Up      { VertexShader = "VertexShader" PixelShader = "PixelShader" }
Effect Down    { VertexShader = "VertexShader" PixelShader = "PixelShader" }
Effect Over    { VertexShader = "VertexShader" PixelShader = "PixelShader" }
Effect Disable { VertexShader = "VertexShader" PixelShader = "PixelShader" }
