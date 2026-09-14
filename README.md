# pfa-week01
Control Name,Type,Range / Options,Description
Object Count,Slider / Field,1 to 50,Total number of procedural primitive meshes to instantiate.
Spread,Slider / Field,1.0 to 100.0,Half-width of the 3D distribution grid in scene units.
Object Size,Slider / Field,0.1 to 20.0,Base scale modifier for generated geometry.
Colour Randomness,Slider / Field,0.0 to 10.0,0.0 yields cohesive hues; 10.0 creates fully randomized palettes.
Random Seed,Integer Field,0 (Disabled) or 1+,Set to 0 for continuous randomness; non-zero values enable reproducible scatters.
Ground Plane Lock,Checkbox,True / False,"When checked (City Mode), object Y-positions snap to the ground grid via bounding box calculations."
Generate Button,Action Button,—,Triggers procedural geometry and shader generation.
Clear Scene,Action Button,—,"Safely deletes tool-generated nodes (RandomCity_GRP, randGeo_*, randMat_*)."
Reset Settings,Action Button,—,Restores all UI sliders and inputs to factory default values.
