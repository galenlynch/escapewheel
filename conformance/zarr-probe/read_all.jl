using Pkg; Pkg.activate(joinpath(ENV["HOME"], ".julia", "environments", "zarrtest"); io=devnull)
using Zarr

# Each set's expected.json maps array to sum, except write.py's, which holds one "sum" for all.
println("Zarr.jl ", pkgversion(Zarr), "  julia ", VERSION)
for set in ("arrays", "more", "writer_arrays", "endian")
    index = joinpath(@__DIR__, set, "expected.json")
    isfile(index) || continue
    text = read(index, String)
    sums = Dict(m[1] => parse(Int, m[2]) for m in eachmatch(r"\"(\w+)\": (-?\d+)", text))
    if haskey(sums, "sum")
        total = sums["sum"]
        sums = Dict(d => total for d in readdir(joinpath(@__DIR__, set)) if isdir(joinpath(@__DIR__, set, d)))
    end
    for (name, expected) in sort(collect(sums))
        try
            s = sum(Int64.(zopen(joinpath(@__DIR__, set, name))[:]))
            println(set, "/", name, ": ", s == expected ? "READ OK" : "WRONG $s")
        catch error
            println(set, "/", name, ": FAIL ", first(first(split(sprint(showerror, error), '\n')), 150))
        end
    end
end
