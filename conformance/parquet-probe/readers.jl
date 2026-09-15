# Parquet2.jl and DuckDB.jl against the files `readers.py` wrote, each compared with its own read of
# the plain file. Parquet2.jl logs each refusal to stderr as well as raising it, so discard stderr.
#
#     julia --startup-file=no readers.jl <scratch directory> 2>/dev/null
using Pkg; Pkg.activate(joinpath(ENV["HOME"], ".julia", "environments", "zarrtest"); io=devnull)
using Parquet2, DuckDB, DataFrames

const con = DBInterface.connect(DuckDB.DB)
readers = [
    "Parquet2.jl $(pkgversion(Parquet2))" => p -> DataFrame(Parquet2.Dataset(p); copycols=true),
    "DuckDB.jl $(pkgversion(DuckDB))" => p -> DataFrame(DBInterface.execute(con, "select * from '$p'")),
]
dir = ARGS[1]
paths = sort(filter(f -> endswith(f, ".parquet") && !startswith(f, "scale-"), readdir(dir; join=true)))
for (label, read) in readers
    println(label)
    for path in paths
        plain = replace(path, r"-[a-z_]+\.parquet$" => "-plain.parquet")
        result = try
            isequal(read(path), read(plain)) ? "ok" : "WRONG"
        catch e
            "FAIL " * first(split(sprint(showerror, e), '\n'))
        end
        println("  ", rpad(splitext(basename(path))[1], 32), " ", result)
    end
end
