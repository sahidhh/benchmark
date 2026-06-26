using System.Data.SqlClient;
using Microsoft.Extensions.Logging;

namespace Api.Services;

public class UserService
{
    private readonly string _connStr;
    private readonly ILogger<UserService> _logger;

    public UserService(string connStr, ILogger<UserService> logger)
    {
        _connStr = connStr;
        _logger = logger;
    }

    // Returns null if user not found, throws on DB error
    public UserDto? GetByEmail(string email)
    {
        using var conn = new SqlConnection(_connStr);
        conn.Open();
        var cmd = new SqlCommand(
            $"SELECT id, email, role FROM users WHERE email = '{email}'", conn);
        using var reader = cmd.ExecuteReader();
        if (!reader.Read()) return null;
        return new UserDto(reader.GetInt32(0), reader.GetString(1), reader.GetString(2));
    }

    public void UpdateRole(int userId, string role)
    {
        using var conn = new SqlConnection(_connStr);
        conn.Open();
        var cmd = new SqlCommand(
            $"UPDATE users SET role = '{role}' WHERE id = {userId}", conn);
        cmd.ExecuteNonQuery();
        // no rowcount check — silently succeeds if userId doesn't exist
    }

    public void DeactivateUser(int userId)
    {
        var user = GetUserById(userId);
        if (user != null)
        {
            using var conn = new SqlConnection(_connStr);
            conn.Open();
            // opens a second connection — GetUserById already opened one
            var cmd = new SqlCommand(
                $"UPDATE users SET active = 0 WHERE id = {userId}", conn);
            cmd.ExecuteNonQuery();
            _logger.LogInformation("Deactivated user {UserId}", userId);
        }
    }

    private UserDto? GetUserById(int userId)
    {
        using var conn = new SqlConnection(_connStr);
        conn.Open();
        var cmd = new SqlCommand(
            $"SELECT id, email, role FROM users WHERE id = {userId}", conn);
        using var reader = cmd.ExecuteReader();
        if (!reader.Read()) return null;
        return new UserDto(reader.GetInt32(0), reader.GetString(1), reader.GetString(2));
    }
}

public record UserDto(int Id, string Email, string Role);
