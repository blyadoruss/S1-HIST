Includes = { "buttonstate.fxh" }

PixelShader = {
    Samplers = {
        MapTexture = {
            Index = 0
            MagFilter = "Point"
            MinFilter = "Point"
            MipFilter = "None"
            AddressU = "Clamp"
            AddressV = "Clamp"
        }
    }
}
VertexStruct VS_OUTPUT {
    float4 vPosition : PDX_POSITION;
    float2 sampleUV : TEXCOORD0;
};
VertexShader = {
    MainCode VertexShader
    [[
        VS_OUTPUT main(const VS_INPUT v) {
            VS_OUTPUT o;
            float2 uv = saturate(v.vTexCoord * float2(20.0, 1.0));
            o.vPosition = mul(WorldViewProjectionMatrix, float4(v.vPosition.xyz, 1));
            o.vPosition.xy = (float2(uv.x, 1.0 - uv.y) * 2.0 - 1.0) * o.vPosition.w;
            o.sampleUV = float2(Offset.x + 0.025, NextOffset.x + 0.025);
            return o;
        }
    ]]
}
PixelShader = {
    MainCode DrawFade
    [[
        float4 main(VS_OUTPUT v) : PDX_COLOR {
            float a = tex2D(MapTexture, float2(v.sampleUV.x, 0.5)).a;
            float b = tex2D(MapTexture, float2(v.sampleUV.y, 0.5)).a;
            return float4(0, 0, 0, lerp(a,b,AnimationTime));
        }
    ]]
}
BlendState BlendState {
    BlendEnable = yes
    SourceBlend = "src_alpha"
    DestBlend = "inv_src_alpha"
}
Effect Up { VertexShader = "VertexShader" PixelShader = "DrawFade" }
Effect Over { VertexShader = "VertexShader" PixelShader = "DrawFade" }
Effect Down { VertexShader = "VertexShader" PixelShader = "DrawFade" }
Effect Disable { VertexShader = "VertexShader" PixelShader = "DrawFade" }
