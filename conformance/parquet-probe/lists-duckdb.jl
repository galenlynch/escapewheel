using Pkg; Pkg.activate(joinpath(ENV["HOME"],".julia","environments","zarrtest"); io=devnull)
f = joinpath(@__DIR__, "lists.parquet")

println("--- Parquet2.jl ---")
try
    using Parquet2, DataFrames
    df = DataFrame(Parquet2.Dataset(f); copycols=false)
    println("  columns: ", names(df))
    println("  spike_ticks[1] = ", df.spike_ticks[1], "   eltype ", eltype(df.spike_ticks))
    println("  tick sum = ", sum(sum(x) for x in df.spike_ticks), " (expect 450)")
    println("  tags[1] = ", df.tags[1], "  tags[3] = ", df.tags[3])
catch e
    println("  FAIL ", first(split(sprint(showerror, e), '\n'), 2))
end

println("\n--- DuckDB.jl ---")
try
    using DuckDB, DataFrames
    con = DBInterface.connect(DuckDB.DB)
    df = DataFrame(DBInterface.execute(con, "SELECT * FROM '$f'"))
    println("  spike_ticks[1] = ", df.spike_ticks[1], "   eltype ", eltype(df.spike_ticks))
    println("  tick sum = ", sum(sum(x) for x in df.spike_ticks), " (expect 450)")
    r = DBInterface.execute(con, "SELECT SUM(t) s FROM (SELECT UNNEST(spike_ticks) t FROM '$f')")
    println("  via UNNEST in SQL = ", first(DataFrame(r).s))
catch e
    println("  FAIL ", first(split(sprint(showerror, e), '\n'), 2))
end
