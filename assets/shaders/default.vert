//http://nehe.gamedev.net/article/glsl_an_introduction/25007/
varying vec3 normal;
varying vec3 vertex_to_light_vector;
 
void main()
{
	gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;

	normal = gl_NormalMatrix * gl_Normal;

	vec4 vertex_in_modelview_space = gl_ModelViewMatrix * gl_Vertex;
	vertex_to_light_vector = vec3(gl_LightSource[0].position - vertex_in_modelview_space);

	gl_TexCoord[0] = gl_MultiTexCoord0;
	gl_FrontColor = gl_Color;
	gl_BackColor = gl_Color;
}

