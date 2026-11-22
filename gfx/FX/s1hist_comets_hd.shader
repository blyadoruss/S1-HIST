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
            float frameCount = 80.0;
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
            // Each frame is a 40 x 30 grid of 48-pixel tiles. The top 80 atlas
            // rows store one lookup table per frame. Two alpha bytes encode x,y.
            float2 texel = 1.0 / float2(4000.0, 3880.0);
            float2 cell = min(floor(v.framePixel.xy / 48.0), float2(39.0, 29.0));
            float entry = (cell.y * 40.0 + cell.x) * 2.0;
            float2 lookup = float2(entry + 0.5, v.framePixel.z) * texel;
            float column = tex2D(MapTexture, lookup).a;
            float row = tex2D(MapTexture, lookup + float2(texel.x, 0)).a;
            float2 tile = floor(float2(column, row) * 255.0 + 0.5);

            // Tile (0,0) is transparent. A one-pixel border on every tile
            // provides the neighbouring source pixels for seamless filtering.
            float2 localPixel = v.framePixel.xy - cell * 48.0;
            float2 atlasPixel = float2(1.0, 81.0) + tile * 50.0 + localPixel;
            float4 comet = tex2D(MapTexture, atlasPixel * texel);

            return comet * float4(Color.rgb * Color.a, Color.a);
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
