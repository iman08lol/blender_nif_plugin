"""This script contains helper methods to managing importing texture into specific slots."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2020, NIF File Format Library and Tools contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above
#   copyright notice, this list of conditions and the following
#   disclaimer in the documentation and/or other materials provided
#   with the distribution.
#
# * Neither the name of the NIF File Format Library and Tools
#   project nor the names of its contributors may be used to endorse
#   or promote products derived from this software without specific
#   prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENSE BLOCK *****


from pyffi.formats.nif import NifFormat

from io_scene_nif.modules.nif_import.geometry.vertex import Vertex
from io_scene_nif.modules.nif_import.property.texture.loader import TextureLoader
from io_scene_nif.utils.util_logging import NifLog
from io_scene_nif.utils.util_nodes import nodes_iterate

# dictionary of texture files, to reuse textures
DICT_TEXTURES = {}

# TODO [property][texture] Move IMPORT_EMBEDDED_TEXTURES as a import property
IMPORT_EMBEDDED_TEXTURES = False

"""Names (ordered by default index) of shader texture slots for Sid Meier's Railroads and similar games."""
EXTRA_SHADER_TEXTURES = [
    "EnvironmentMapIndex",
    "NormalMapIndex",
    "SpecularIntensityIndex",
    "EnvironmentIntensityIndex",
    "LightCubeMapIndex",
    "ShadowTextureIndex"]


class TextureSlotManager:

    def __init__(self):
        self.texture_loader = TextureLoader()
        self.tree = None
        self.b_mat = None
        self.output = None
        self.diffuse_pass = None
        self.diffuse_shader = None
        # raw texture nodes
        self.diffuse_texture = None

    def clear_default_nodes(self):
        self.b_mat.use_nodes = True
        self.tree = self.b_mat.node_tree
        # clear default nodes
        for node in self.tree.nodes:
            self.tree.nodes.remove(node)

        self.output = self.tree.nodes.new('ShaderNodeOutputMaterial')
        # principled = self.tree.nodes.new('ShaderNodeBsdfPrincipled')

        # shaders
        self.diffuse_shader = self.tree.nodes.new('ShaderNodeBsdfDiffuse')

        # image passes
        self.diffuse_pass = None

        # raw texture nodes
        self.diffuse_texture = None

    def connect_to_pass(self, b_node_pass, b_texture_node):
        """Connect to an image premixing pass"""
        # connect
        if b_node_pass:
            mixRGB = self.tree.nodes.new('ShaderNodeMixRGB')
            mixRGB.inputs[0].default_value = 1
            mixRGB.blend_type = "OVERLAY"
            self.tree.links.new(b_node_pass.outputs[0], mixRGB.inputs[1])
            self.tree.links.new(b_texture_node.outputs[0], mixRGB.inputs[2])
            return mixRGB
        return b_texture_node

    def connect_to_output(self):

        if self.diffuse_pass:
            try:
                self.tree.links.new(self.diffuse_pass.outputs[0], self.diffuse_shader.inputs[0])
            except:
                print("bug")
        # transparency
        if self.b_mat.blend_method == "OPAQUE":
            self.tree.links.new(self.diffuse_shader.outputs[0], self.output.inputs[0])
        else:
            transp = self.tree.nodes.new('ShaderNodeBsdfTransparent')
            alpha_mixer = self.tree.nodes.new('ShaderNodeMixShader')
            #
            # if textures and ob.data.vertex_colors:
            #     vcol = tree.nodes.new('ShaderNodeAttribute')
            #     vcol.attribute_name = "AAA"
            #     mixAAA = tree.nodes.new('ShaderNodeMixRGB')
            #     mixAAA.inputs[0].default_value = 1
            #     mixAAA.blend_type = "MULTIPLY"
            #     tree.links.new(textures[0].outputs[1], mixAAA.inputs[1])
            #     tree.links.new(vcol.outputs[0], mixAAA.inputs[2])
            #     tree.links.new(mixAAA.outputs[0], alpha_mixer.inputs[0])
            if self.diffuse_texture:
                print("self.diffuse_texture", self.diffuse_texture)
                try:
                    self.tree.links.new(self.diffuse_texture.outputs[1], alpha_mixer.inputs[0])
                except:
                    print("Bug in tex sys setting alpha channel, happens in successive runs?")
            # elif ob.data.vertex_colors:
            #     vcol = tree.nodes.new('ShaderNodeAttribute')
            #     vcol.attribute_name = "AAA"
            #     tree.links.new(vcol.outputs[0], alpha_mixer.inputs[0])

            self.tree.links.new(transp.outputs[0], alpha_mixer.inputs[1])
            self.tree.links.new(self.diffuse_shader.outputs[0], alpha_mixer.inputs[2])
            self.tree.links.new(alpha_mixer.outputs[0], self.output.inputs[0])

        nodes_iterate(self.tree, self.output)

    def create_texture_slot(self, b_mat, n_tex_desc):
        print(n_tex_desc)
        # todo [texture] refactor this to separate code paths?
        # when processing a texturing property
        if isinstance(n_tex_desc, NifFormat.TexDesc):
            b_texture_node = self.texture_loader.import_texture_source(n_tex_desc.source, b_mat.node_tree)
            uv_layer_name = n_tex_desc.uv_set
        # when processing a texturing property - n_tex_desc is a bare string
        else:
            b_texture_node = self.texture_loader.import_texture_source(n_tex_desc, b_mat.node_tree)
            uv_layer_name = 0


        # Mapping
        # b_texture_node.texture_coords = 'UV'
        # b_texture_node.uv_layer = Vertex.get_uv_layer_name(uv_layer_name)
        return b_texture_node

    def link_diffuse_node(self, b_texture_node):
        print("b_texture_node", b_texture_node)
        self.diffuse_texture = b_texture_node
        print("self.diffuse_texture", self.diffuse_texture)
        b_texture_node.label = "Diffuse"
        self.diffuse_pass = self.connect_to_pass(self.diffuse_pass, b_texture_node)

    def update_bump_slot(self, b_texture_node):
        b_texture_node.label = "Bump"
        # # Influence mapping
        # b_texture_node.texture.use_normal_map = False  # causes artifacts otherwise.
        #
        # # Influence
        # # TODO [property][texture][flag][alpha] Figure out if this texture has alpha
        # # if self.nif_import.ni_alpha_prop:
        # #     b_texture_node.use_map_alpha = True
        #
        # b_texture_node.use_map_color_diffuse = False
        # b_texture_node.use_map_normal = True
        # b_texture_node.use_map_alpha = False

    def update_normal_slot(self, b_texture_node):
        b_texture_node.label = "Normal"
        # # Influence mapping
        # b_texture_node.texture.use_normal_map = True  # causes artifacts otherwise.
        #
        # # Influence
        # # TODO [property][texture][flag][alpha] Figure out if this texture has alpha
        # # if self.nif_import.ni_alpha_prop:
        # #     b_texture_node.use_map_alpha = True
        #
        # b_texture_node.use_map_color_diffuse = False
        # b_texture_node.use_map_normal = True
        # b_texture_node.use_map_alpha = False

    def update_glow_slot(self, b_texture_node):
        b_texture_node.label = "Glow"
        # # Influence mapping
        # b_texture_node.texture.use_alpha = False
        #
        # # Influence
        # # TODO [property][texture][flag][alpha] Figure out if this texture has alpha
        # # if self.nif_import.ni_alpha_prop:
        # #     b_texture_node.use_map_alpha = True
        #
        # b_texture_node.use_map_color_diffuse = False
        # b_texture_node.use_map_emit = True

    def update_gloss_slot(self, b_texture_node):
        b_texture_node.label = "Gloss"
        # # Influence mapping
        # b_texture_node.texture.use_alpha = False
        #
        # # Influence
        # # TODO [property][texture][flag][alpha] Figure out if this texture has alpha
        # # if self.nif_import.ni_alpha_prop:
        # #     b_texture_node.use_map_alpha = True
        #
        # b_texture_node.use_map_color_diffuse = False
        # b_texture_node.use_map_specular = True
        # b_texture_node.use_map_color_spec = True

    def update_decal_slot(self, b_texture_node):
        # self.update_decal_slot(b_texture_node)
        # TODO [property][texture] Add support for decal slots
        NifLog.warn("This functionality is not currently supported")
        pass

    def update_decal_slot_0(self, b_texture_node):
        self.update_decal_slot(b_texture_node)
        # TODO [property][texture] Add support for decal slots

    def update_decal_slot_1(self, b_texture_node):
        self.update_decal_slot(b_texture_node)
        # TODO [property][texture] Add support for decal slots

    def update_detail_slot(self, b_texture_node):
        b_texture_node.label = "Detail"
        self.diffuse_pass = self.connect_to_pass(self.diffuse_pass, b_texture_node)

    def update_decal_slot_2(self, b_texture_node):
        self.update_decal_slot(b_texture_node)

    def update_dark_slot(self, b_texture_node):
        self.update_decal_slot(b_texture_node)
        b_texture_node.blend_type = 'DARK'

    def update_reflection_slot(self, b_texture_node):
        # Influence mapping

        # Influence
        # TODO [property][texture][flag][alpha] Figure out if this texture has alpha
        # if self.nif_import.ni_alpha_prop:
        #     b_texture_node.use_map_alpha = True

        b_texture_node.use_map_color_diffuse = True
        b_texture_node.use_map_emit = True
        b_texture_node.use_map_mirror = True

    def update_environment_slot(self, b_texture_node):
        # Influence mapping

        # Influence
        # TODO [property][texture][flag][alpha] Figure out if this texture has alpha
        # if self.nif_import.ni_alpha_prop:
        #     b_texture_node.use_map_alpha = True

        b_texture_node.use_map_color_diffuse = True
        b_texture_node.blend_type = 'ADD'

    @staticmethod
    def get_b_blend_type_from_n_apply_mode(n_apply_mode):
        # TODO [material] Check out n_apply_modes
        if n_apply_mode == NifFormat.ApplyMode.APPLY_MODULATE:
            return "MIX"
        elif n_apply_mode == NifFormat.ApplyMode.APPLY_REPLACE:
            return "COLOR"
        elif n_apply_mode == NifFormat.ApplyMode.APPLY_DECAL:
            return "OVERLAY"
        elif n_apply_mode == NifFormat.ApplyMode.APPLY_HILIGHT:
            return "LIGHTEN"
        elif n_apply_mode == NifFormat.ApplyMode.APPLY_HILIGHT2:  # used by Oblivion for parallax
            return "MULTIPLY"
        else:
            NifLog.warn("Unknown apply mode (%i) in material, using blend type 'MIX'".format(n_apply_mode))
            return "MIX"
