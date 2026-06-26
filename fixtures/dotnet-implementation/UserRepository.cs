using System.Data.SqlClient;
using Api.Models;

namespace Api.Repositories;

public class UserRepository
{
    private readonly string _connStr;

    public UserRepository(string connStr)
    {
        _connStr = connStr;
    }

    public async Task<User?> FindByEmailAsync(string email)
    {
        using var conn = new SqlConnection(_connStr);
        await conn.OpenAsync();
        var cmd = new SqlCommand(
            "SELECT id, email, username, password_hash, created_at, active FROM users WHERE email = @email",
            conn);
        cmd.Parameters.AddWithValue("@email", email);
        return await ReadUserAsync(cmd);
    }

    public async Task<User?> FindByIdAsync(int id)
    {
        using var conn = new SqlConnection(_connStr);
        await conn.OpenAsync();
        var cmd = new SqlCommand(
            "SELECT id, email, username, password_hash, created_at, active FROM users WHERE id = @id",
            conn);
        cmd.Parameters.AddWithValue("@id", id);
        return await ReadUserAsync(cmd);
    }

    public async Task<User> InsertAsync(User user)
    {
        using var conn = new SqlConnection(_connStr);
        await conn.OpenAsync();
        var cmd = new SqlCommand(
            "INSERT INTO users (email, username, password_hash, created_at, active) " +
            "OUTPUT INSERTED.id " +
            "VALUES (@email, @username, @passwordHash, @createdAt, @active)", conn);
        cmd.Parameters.AddWithValue("@email", user.Email);
        cmd.Parameters.AddWithValue("@username", user.Username);
        cmd.Parameters.AddWithValue("@passwordHash", user.PasswordHash);
        cmd.Parameters.AddWithValue("@createdAt", user.CreatedAt);
        cmd.Parameters.AddWithValue("@active", user.Active);
        user.Id = (int)await cmd.ExecuteScalarAsync();
        return user;
    }

    private static async Task<User?> ReadUserAsync(SqlCommand cmd)
    {
        using var reader = await cmd.ExecuteReaderAsync();
        if (!await reader.ReadAsync()) return null;
        return new User
        {
            Id = reader.GetInt32(0),
            Email = reader.GetString(1),
            Username = reader.GetString(2),
            PasswordHash = reader.GetString(3),
            CreatedAt = reader.GetDateTime(4),
            Active = reader.GetBoolean(5),
        };
    }
}
