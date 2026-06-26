using Api.Models;
using Api.Repositories;

namespace Api.Services;

public class UserService
{
    private readonly UserRepository _repo;
    private readonly NotificationService _notifications;

    public UserService(UserRepository repo, NotificationService notifications)
    {
        _repo = repo;
        _notifications = notifications;
    }

    public async Task<UserDto> RegisterAsync(string email, string username, string passwordHash)
    {
        var existing = await _repo.FindByEmailAsync(email);
        if (existing != null)
            throw new InvalidOperationException("Email already registered");

        var user = await _repo.InsertAsync(new User
        {
            Email = email,
            Username = username,
            PasswordHash = passwordHash,
            CreatedAt = DateTime.UtcNow,
            Active = true,
        });

        await _notifications.SendWelcomeEmailAsync(email, username);
        return new UserDto(user.Id, user.Email, user.Username);
    }

    public async Task<UserDto?> GetByIdAsync(int id)
    {
        var user = await _repo.FindByIdAsync(id);
        if (user == null) return null;
        return new UserDto(user.Id, user.Email, user.Username);
    }
}

public record UserDto(int Id, string Email, string Username);
