using Microsoft.Extensions.Logging;

namespace Api.Services;

public class NotificationService
{
    private readonly IEmailSender _emailSender;
    private readonly ILogger<NotificationService> _logger;

    public NotificationService(IEmailSender emailSender, ILogger<NotificationService> logger)
    {
        _emailSender = emailSender;
        _logger = logger;
    }

    public async Task SendWelcomeEmailAsync(string toEmail, string username)
    {
        var subject = "Welcome!";
        var body = $"Hi {username}, welcome to the platform.";
        await _emailSender.SendAsync(toEmail, subject, body);
        _logger.LogInformation("Sent welcome email to {Email}", toEmail);
    }

    public async Task SendPasswordResetAsync(string toEmail, string resetToken)
    {
        var subject = "Reset your password";
        var body = $"Use this token to reset your password: {resetToken}";
        await _emailSender.SendAsync(toEmail, subject, body);
        _logger.LogInformation("Sent password reset to {Email}", toEmail);
    }
}

public interface IEmailSender
{
    Task SendAsync(string to, string subject, string body);
}
