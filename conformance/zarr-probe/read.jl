using Pkg; Pkg.activate(joinpath(ENV["HOME"],".julia","environments","zarrtest"); io=devnull)
using Zarr

const EXPECTED = -365664
base = joinpath(@__DIR__, "arrays")
dirs = ["v3_raw","v3_gzip","v3_zstd","v3_blosc_zstd_shuffle","v3_sharded_zstd","v2_zstd","v2_blosc_zstd_shuffle"]

println("Zarr.jl ", pkgversion(Zarr), "  julia ", VERSION, "\n")
for d in dirs
    print(rpad(d, 24), " ")
    try
        a = zopen(joinpath(base, d))
        v = a[:, :]
        s = sum(Int64.(v))
        if s == EXPECTED
            println("READ OK      size=", size(v), " eltype=", eltype(v))
        else
            println("WRONG VALUES sum=", s, " expected=", EXPECTED)
        end
    catch e
        msg = first(split(sprint(showerror, e), '\n'))
        println("FAIL         ", first(msg, 150))
    end
end
