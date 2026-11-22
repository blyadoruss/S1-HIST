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
    float2 vTexCoord : TEXCOORD0;
};

VertexShader = {
    MainCode VertexShader
    [[
        VS_OUTPUT main(const VS_INPUT v)
        {
            VS_OUTPUT Out;
            Out.vPosition = mul(WorldViewProjectionMatrix, float4(v.vPosition, 1.0));

            // frameAnimatedSpriteType supplies a horizontal offset for the current frame.
            float frame = floor(Offset.x * 160.0 + 0.5);
            float2 uv = saturate(v.vTexCoord * float2(160.0, 1.0));

            // Cover the viewport with a centred 4:3 frame, cropping the overflow.
            float clipWidth = mul(WorldViewProjectionMatrix, float4(1, 0, 0, 0)).x;
            float clipHeight = mul(WorldViewProjectionMatrix, float4(0, 1, 0, 0)).y;
            float aspectRatio = abs(clipHeight / clipWidth);
            float2 cover = max(float2(1, 1), float2(4.0 / (3.0 * aspectRatio), aspectRatio * 0.75));
            Out.vPosition.xy = (float2(uv.x, 1.0 - uv.y) * 2.0 - 1.0) * cover * Out.vPosition.w;

            // Remap the logical strip to the 10-column atlas.
            float row = floor(frame / 10.0);
            float2 cell = float2(frame - row * 10.0, row);
            // Sample between texel centres so adjacent frames cannot bleed in.
            float2 pixel = 0.5 + uv * float2(319.0, 239.0);
            Out.vTexCoord = (cell + pixel / float2(320.0, 240.0)) / float2(10.0, 16.0);
            return Out;
        }
    ]]
}

PixelShader = {
    MainCode PixelShader
    [[
        float4 main(VS_OUTPUT v) : PDX_COLOR
        {
            return tex2D(MapTexture, v.vTexCoord) * Color;
        }
    ]]
}

BlendState BlendState
{
    BlendEnable = yes
    SourceBlend = "src_alpha"
    DestBlend = "inv_src_alpha"
}

Effect Up      { VertexShader = "VertexShader" PixelShader = "PixelShader" }
Effect Down    { VertexShader = "VertexShader" PixelShader = "PixelShader" }
Effect Over    { VertexShader = "VertexShader" PixelShader = "PixelShader" }
Effect Disable { VertexShader = "VertexShader" PixelShader = "PixelShader" }
