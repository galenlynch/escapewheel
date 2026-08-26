using Pkg; Pkg.activate(joinpath(ENV["HOME"],".julia","environments","zarrtest"); io=devnull)
using Parquet2, DataFrames
println("Parquet2.jl ", pkgversion(Parquet2))
for kind in ("prim","list"), comp in ("zstd","snappy","none")
    f = joinpath(@__DIR__, "ctl_$(kind)_$(comp).parquet")
    print(rpad("$kind / $comp", 16))
    try
        df = DataFrame(Parquet2.Dataset(f); copycols=false)
        println("OK  ", size(df), "  ", kind=="list" ? repr(df[1,2]) : "")
    catch e
        println("FAIL ", first(first(split(sprint(showerror, e), '\n'), 1)))
    end
end
