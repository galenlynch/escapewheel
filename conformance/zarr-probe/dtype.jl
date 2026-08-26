using Pkg; Pkg.activate(joinpath(ENV["HOME"],".julia","environments","zarrtest"); io=devnull)
using Zarr
a = zopen(joinpath(@__DIR__, "arrays", "v3_zstd"))
println("Zarr.jl metadata.dtype = ", a.metadata.dtype, "  (typeof ", typeof(a.metadata.dtype), ")")
println("Zarr.jl eltype(a)      = ", eltype(a))
