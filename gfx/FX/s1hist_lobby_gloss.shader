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
VertexStruct VS_OUTPUT {
    float4 vPosition : PDX_POSITION;
    float2 uv : TEXCOORD0;
    float2 face : TEXCOORD1;
};
VertexShader = {
    MainCode VertexShader
    [[
        VS_OUTPUT main(const VS_INPUT v) {
            VS_OUTPUT o;
            o.vPosition = mul(WorldViewProjectionMatrix, float4(v.vPosition.xyz, 1));
            o.uv = v.vTexCoord + Offset;
            o.face = v.vTexCoord * float2(3.0, 1.0);
            return o;
        }
    ]]
}
PixelShader = {
    Code [[
        float4 finishButton(VS_OUTPUT v, float strength) {
            float4 base = tex2D(MapTexture, v.uv);
            float2 p = saturate(v.face);
            float edge = min(min(p.x, 1.0-p.x)*288.0, min(p.y, 1.0-p.y)*36.0);
            float coat = smoothstep(1.0, 3.0, edge);
            float curve = 0.42 + 0.08 * (1.0 - p.x) * (1.0 - p.x);
            float reflection = (1.0-smoothstep(curve-0.06,curve+0.03,p.y)) * (0.36+0.55*p.y);
            float glint = exp2(-8.0*abs(p.x-0.30+0.22*p.y)) * (1.0-p.y);
            float rim = exp2(-1.6*abs(p.y*36.0-2.6));
            base.rgb += strength * coat * (reflection+0.42*glint+0.45*rim) * float3(0.54,0.72,1.0);
            return base * Color;
        }
    ]]
    MainCode Normal [[ float4 main(VS_OUTPUT v) : PDX_COLOR { return finishButton(v, 0.19); } ]]
    MainCode Hover [[ float4 main(VS_OUTPUT v) : PDX_COLOR { return finishButton(v, 0.40); } ]]
    MainCode Pressed [[ float4 main(VS_OUTPUT v) : PDX_COLOR { return finishButton(v, 0.10); } ]]
    MainCode Disabled [[
        float4 main(VS_OUTPUT v) : PDX_COLOR {
            float4 c = tex2D(MapTexture,v.uv);
            c.rgb = dot(c.rgb,float3(0.212671,0.715160,0.072169)).xxx;
            return c * Color;
        }
    ]]
}
BlendState BlendState {
    BlendEnable = yes
    SourceBlend = "src_alpha"
    DestBlend = "inv_src_alpha"
}
Effect Up { VertexShader = "VertexShader" PixelShader = "Normal" }
Effect Over { VertexShader = "VertexShader" PixelShader = "Hover" }
Effect Down { VertexShader = "VertexShader" PixelShader = "Pressed" }
Effect Disable { VertexShader = "VertexShader" PixelShader = "Disabled" }