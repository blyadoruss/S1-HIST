# SICORUM simple RGBA sprite shader for Hearts of Iron IV.
# Experimental optional shader; the provided .gfx uses a built-in vanilla effect for maximum compatibility.
# No cyan glow, additive flash, recolouring, or opacity pulse.
Includes = {
    "buttonstate.fxh"
    "sprite_animation.fxh"
}

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
    float2 vTexCoord : TEXCOORD0;
};

VertexShader = {
    MainCode VertexShaderSicorum
    [[
        VS_OUTPUT main(const VS_INPUT v) {
            VS_OUTPUT Out;
            Out.vPosition = mul(WorldViewProjectionMatrix, float4(v.vPosition.xyz, 1));
            Out.vTexCoord = v.vTexCoord;
            return Out;
        }
    ]]
}

PixelShader = {
    MainCode PixelShaderSicorum
    [[
        float4 main(VS_OUTPUT v) : PDX_COLOR {
            return tex2D(MapTexture, v.vTexCoord);
        }
    ]]
}

BlendState BlendState {
    BlendEnable = yes
    SourceBlend = "src_alpha"
    DestBlend = "inv_src_alpha"
}

Effect Up {
    VertexShader = "VertexShaderSicorum"
    PixelShader = "PixelShaderSicorum"
}
Effect Down {
    VertexShader = "VertexShaderSicorum"
    PixelShader = "PixelShaderSicorum"
}
Effect Disable {
    VertexShader = "VertexShaderSicorum"
    PixelShader = "PixelShaderSicorum"
}
Effect Over {
    VertexShader = "VertexShaderSicorum"
    PixelShader = "PixelShaderSicorum"
}
